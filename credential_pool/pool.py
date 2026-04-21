"""
Provider Credential Pool + Auto-Rotating
=========================================
Inspired by OpenClaude Issue #780 (credential pool with rotation).
Manages multiple API keys per provider with automatic rotation on:
- Rate limit (429) errors
- Authentication failures (401/403)
- Quota exhaustion
- Cooldown tracking

Features:
- Pool of credentials per provider (OpenAI, Anthropic, Google, etc.)
- Automatic rotation on failures
- Cooldown periods for rate-limited keys
- Health tracking per key
- Load balancing across healthy keys
- Fallback to next provider when all keys exhausted
"""
import json, os, time, tempfile, threading, hashlib, random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field, asdict
from enum import Enum

BASE_DIR = Path(os.environ.get("OPENCLAW_DIRECTOR_DIR",
    Path.home() / ".openclaw" / "workspaces" / "director"))
POOL_DIR = BASE_DIR / "credential_pool"
POOL_DIR.mkdir(parents=True, exist_ok=True)
POOL_FILE = POOL_DIR / "credential_pool.json"


class CredentialStatus(str, Enum):
    ACTIVE = "active"         # Available for use
    COOLDOWN = "cooldown"      # Rate-limited, waiting
    EXHAUSTED = "exhausted"   # Quota used up (daily)
    INVALID = "invalid"       # Auth failed permanently
    UNKNOWN = "unknown"       # Not yet tested


@dataclass
class Credential:
    """A single API key/credential with health tracking."""
    cred_id: str; provider: str; api_key: str
    model_prefix: str = ""      # e.g. "gpt-4", "claude-"
    status: CredentialStatus = CredentialStatus.UNKNOWN
    priority: int = 1           # Higher = used first
    total_requests: int = 0
    total_errors: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    last_used: str = ""
    last_error: str = ""
    last_error_code: int = 0
    cooldown_until: str = ""    # ISO timestamp
    daily_limit: float = 0.0   # 0 = unlimited
    daily_used: float = 0.0
    daily_reset: str = ""       # ISO date

    def to_dict(self):
        return {**asdict(self), "status": self.status.value}

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        data["status"] = CredentialStatus(data.get("status", "unknown"))
        return cls(**data)

    def is_available(self) -> bool:
        if self.status == CredentialStatus.INVALID: return False
        if self.status == CredentialStatus.EXHAUSTED: return False
        if self.cooldown_until:
            try:
                cooldown_time = datetime.fromisoformat(self.cooldown_until)
                if datetime.now(timezone.utc) < cooldown_time:
                    return False
                self.status = CredentialStatus.ACTIVE
                self.cooldown_until = ""
            except Exception: pass
        if self.daily_limit > 0 and self.daily_used >= self.daily_limit:
            return False
        return True

    def record_success(self, tokens: int = 0, cost: float = 0.0):
        self.total_requests += 1
        self.total_tokens_used += tokens
        self.total_cost_usd += cost
        self.daily_used += cost
        self.last_used = datetime.now(timezone.utc).isoformat()
        if self.status != CredentialStatus.ACTIVE:
            self.status = CredentialStatus.ACTIVE

    def record_error(self, error_code: int = 0, error_msg: str = ""):
        self.total_errors += 1
        self.last_error = error_msg
        self.last_error_code = error_code
        # Handle specific error codes
        if error_code == 429:  # Rate limit
            self.status = CredentialStatus.COOLDOWN
            cooldown_minutes = min(2 ** (self.total_errors % 5), 60)  # Exponential backoff
            self.cooldown_until = (datetime.now(timezone.utc) +
                timedelta(minutes=cooldown_minutes)).isoformat()
        elif error_code in (401, 403):  # Auth failure
            self.status = CredentialStatus.INVALID
        elif error_code == 402:  # Payment required
            self.status = CredentialStatus.EXHAUSTED


@dataclass
class ProviderPool:
    """Pool of credentials for a single provider."""
    provider: str
    credentials: List[Credential] = field(default_factory=list)
    fallback_provider: str = ""  # Next provider to try if all keys fail

    def get_available(self) -> List[Credential]:
        available = [c for c in self.credentials if c.is_available()]
        available.sort(key=lambda c: c.priority, reverse=True)
        return available

    def get_next(self) -> Optional[Credential]:
        available = self.get_available()
        if not available: return None
        # Round-robin among equally-prioritized keys
        top_priority = available[0].priority
        top = [c for c in available if c.priority == top_priority]
        # Pick least recently used
        top.sort(key=lambda c: c.last_used or "")
        return top[0]

    def get_stats(self) -> dict:
        return {
            "provider": self.provider,
            "total_keys": len(self.credentials),
            "active": len([c for c in self.credentials if c.status == CredentialStatus.ACTIVE]),
            "cooldown": len([c for c in self.credentials if c.status == CredentialStatus.COOLDOWN]),
            "exhausted": len([c for c in self.credentials if c.status == CredentialStatus.EXHAUSTED]),
            "invalid": len([c for c in self.credentials if c.status == CredentialStatus.INVALID]),
            "total_requests": sum(c.total_requests for c in self.credentials),
            "total_cost": round(sum(c.total_cost_usd for c in self.credentials), 4),
            "fallback": self.fallback_provider,
        }


class CredentialPool:
    """
    Global credential pool across all providers.
    Provides automatic rotation, health tracking, and failover.
    """
    def __init__(self, pool_file: Path = POOL_FILE):
        self.pool_file = pool_file
        self.providers: Dict[str, ProviderPool] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if self.pool_file.exists():
            try:
                with open(self.pool_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for pdata in data.get("providers", []):
                    creds = [Credential.from_dict(c) for c in pdata.get("credentials", [])]
                    pool = ProviderPool(provider=pdata["provider"], credentials=creds,
                                        fallback_provider=pdata.get("fallback_provider", ""))
                    self.providers[pool.provider] = pool
            except Exception: pass

    def _save(self):
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self.pool_file.parent), suffix='.tmp')
        try:
            data = {"providers": [
                {"provider": p.provider,
                 "credentials": [c.to_dict() for c in p.credentials],
                 "fallback_provider": p.fallback_provider}
                for p in self.providers.values()],
                "updated": datetime.now(timezone.utc).isoformat()}
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            os.replace(tmp_path, str(self.pool_file))
        except Exception: os.unlink(tmp_path); raise

    def add_credential(self, provider: str, api_key: str,
                       model_prefix: str = "", priority: int = 1,
                       daily_limit: float = 0.0) -> str:
        cred_id = f"cred_{provider}_{hashlib.md5(api_key.encode()).hexdigest()[:8]}"
        cred = Credential(cred_id=cred_id, provider=provider, api_key=api_key,
                          model_prefix=model_prefix, priority=priority,
                          status=CredentialStatus.UNKNOWN,
                          daily_limit=daily_limit,
                          daily_reset=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        if provider not in self.providers:
            self.providers[provider] = ProviderPool(provider=provider)
        self.providers[provider].credentials.append(cred)
        self._save()
        return cred_id

    def get_credential(self, provider: str) -> Optional[Credential]:
        """Get the next available credential for a provider, with fallback."""
        tried_providers = set()
        current = provider
        while current and current not in tried_providers:
            tried_providers.add(current)
            if current in self.providers:
                cred = self.providers[current].get_next()
                if cred: return cred
                # Try fallback
                current = self.providers[current].fallback_provider
            else: break
        return None

    def record_success(self, cred_id: str, provider: str,
                       tokens: int = 0, cost: float = 0.0):
        with self._lock:
            if provider in self.providers:
                for c in self.providers[provider].credentials:
                    if c.cred_id == cred_id:
                        c.record_success(tokens, cost); break
                self._save()

    def record_error(self, cred_id: str, provider: str,
                     error_code: int = 0, error_msg: str = ""):
        with self._lock:
            if provider in self.providers:
                for c in self.providers[provider].credentials:
                    if c.cred_id == cred_id:
                        c.record_error(error_code, error_msg); break
                self._save()

    def set_fallback(self, provider: str, fallback: str):
        if provider in self.providers:
            self.providers[provider].fallback_provider = fallback
            self._save()

    def health_check(self) -> dict:
        """Check health of all credentials and return report."""
        report = {"providers": {}, "total_active": 0, "total_keys": 0,
                  "warnings": []}
        for name, pool in self.providers.items():
            stats = pool.get_stats()
            report["providers"][name] = stats
            report["total_active"] += stats["active"]
            report["total_keys"] += stats["total_keys"]
            if stats["active"] == 0 and stats["total_keys"] > 0:
                report["warnings"].append(f"{name}: No active keys!")
            if stats["cooldown"] > 0:
                report["warnings"].append(f"{name}: {stats['cooldown']} keys in cooldown")
        return report

    def reset_daily(self):
        """Reset daily usage counters."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for pool in self.providers.values():
            for cred in pool.credentials:
                if cred.daily_reset != today:
                    cred.daily_used = 0.0
                    cred.daily_reset = today
                    if cred.status == CredentialStatus.EXHAUSTED:
                        cred.status = CredentialStatus.ACTIVE
        self._save()

    def get_stats(self) -> dict:
        return {"providers": {n: p.get_stats() for n, p in self.providers.items()},
                "total_keys": sum(len(p.credentials) for p in self.providers.values()),
                "total_active": sum(len([c for c in p.credentials if c.is_available()])
                                   for p in self.providers.values())}


_pool: Optional[CredentialPool] = None
def get_credential_pool() -> CredentialPool:
    global _pool
    if _pool is None: _pool = CredentialPool()
    return _pool


if __name__ == "__main__":
    import sys
    pool = get_credential_pool()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats": print(json.dumps(pool.get_stats(), indent=2))
    elif cmd == "health": print(json.dumps(pool.health_check(), indent=2))
    elif cmd == "add" and len(sys.argv) > 4:
        pool.add_credential(sys.argv[2], sys.argv[3],
                            model_prefix=sys.argv[4] if len(sys.argv) > 4 else "",
                            priority=int(sys.argv[5]) if len(sys.argv) > 5 else 1)
        print(f"Added credential for {sys.argv[2]}")
    else:
        print("Commands: stats, health, add <provider> <key> [model_prefix] [priority]")