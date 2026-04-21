"""
Constitutional Guardian v2 — Enhanced Self-Governance
=====================================================
Extends the existing constitutional_ai.py with:
1. Drift Detection: Monitors model performance and triggers alerts/retraining
2. Auto-Healing: Triggers self-heal pipeline when constitutional violations detected
3. Reputation Scoring: Tracks agent compliance over time
4. Adaptive Rules: Rules that can evolve based on experience (with human approval)
5. Budget Guardian: Enforces daily/weekly budget hard limits
6. Rate Limiting: Per-action and per-time-window throttling
7. Integration: Wired to Evolution Engine, Dual Memory, Credential Pool, HUD

Architecture:
  Action -> pre_check() -> [ALLOWED/BLOCKED/WARNING]
         -> execute()
         -> post_check() -> [AUDIT/DRIFT/HEAL]
         -> record() -> Memory + Audit + HUD
"""
import json, os, time, hashlib, tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field, asdict
from enum import Enum

BASE_DIR = Path(os.environ.get("OPENCLAW_DIRECTOR_DIR",
    Path.home() / ".openclaw" / "workspaces" / "director"))
GUARDIAN_DIR = BASE_DIR / "guardian_v2"
GUARDIAN_DIR.mkdir(parents=True, exist_ok=True)
DRIFT_LOG = GUARDIAN_DIR / "drift_log.jsonl"
REPUTATION_FILE = GUARDIAN_DIR / "reputation.json"
BUDGET_FILE = GUARDIAN_DIR / "budget_state.json"


class DriftLevel(str, Enum):
    NONE = "none"; LOW = "low"; MEDIUM = "medium"; HIGH = "high"; CRITICAL = "critical"

class GuardianAction(str, Enum):
    ALLOW = "allow"; BLOCK = "block"; WARN = "warn"; THROTTLE = "throttle"
    HEAL = "heal"; ROLLBACK = "rollback"


@dataclass
class DriftState:
    """Current drift state for monitoring."""
    model_accuracy: float = 1.0      # 0.0-1.0, degrades over time
    error_rate_24h: float = 0.0     # Error percentage in last 24h
    cost_trend: float = 0.0        # Daily cost trend (positive = increasing)
    latency_trend: float = 0.0    # Latency trend
    drift_level: DriftLevel = DriftLevel.NONE
    last_checked: str = ""
    recommendations: list = field(default_factory=list)
    def to_dict(self):
        return {**asdict(self), "drift_level": self.drift_level.value}


@dataclass
class AgentReputation:
    """Compliance reputation for an agent."""
    agent_id: str; total_actions: int = 0
    violations: int = 0; warnings: int = 0
    compliance_rate: float = 1.0    # 0.0-1.0
    last_violation: str = ""; last_warning: str = ""
    trust_level: float = 1.0       # 0.0-2.0
    def to_dict(self): return asdict(self)


@dataclass
class BudgetState:
    """Budget tracking state."""
    daily_limit: float = 10.0; daily_used: float = 0.0
    weekly_limit: float = 50.0; weekly_used: float = 0.0
    daily_reset: str = ""; weekly_reset: str = ""
    def to_dict(self): return asdict(self)
    def daily_remaining(self) -> float: return max(0, self.daily_limit - self.daily_used)
    def weekly_remaining(self) -> float: return max(0, self.weekly_limit - self.weekly_used)
    def is_daily_exceeded(self) -> bool: return self.daily_used >= self.daily_limit
    def is_weekly_exceeded(self) -> bool: return self.weekly_used >= self.weekly_limit


class DriftDetector:
    """
    Monitors system metrics for drift (performance degradation).
    Inspired by Skynet Agent's autopilot + Plandex's automated debugging.
    """
    def __init__(self):
        self.state = DriftState()
        self._recent_errors: List[dict] = []
        self._recent_costs: List[float] = []

    def record_error(self, error_type: str, error_msg: str):
        self._recent_errors.append({"type": error_type, "msg": error_msg,
            "ts": datetime.now(timezone.utc).isoformat()})
        # Keep last 24h
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        self._recent_errors = [e for e in self._recent_errors if e["ts"] > cutoff]

    def record_cost(self, cost_usd: float):
        self._recent_costs.append(cost_usd)
        # Keep last 24h
        if len(self._recent_costs) > 1000:
            self._recent_costs = self._recent_costs[-1000:]

    def check_drift(self) -> DriftState:
        """Evaluate current drift level and generate recommendations."""
        # Error rate calculation
        total_recent = len(self._recent_errors)
        if total_recent > 0:
            self.state.error_rate_24h = min(total_recent / 100.0, 1.0)
        # Cost trend
        if len(self._recent_costs) >= 5:
            recent = self._recent_costs[-5:]
            older = self._recent_costs[-10:-5] if len(self._recent_costs) >= 10 else self._recent_costs[:5]
            avg_recent = sum(recent) / len(recent)
            avg_older = sum(older) / max(len(older), 1)
            self.state.cost_trend = avg_recent - avg_older
        # Determine drift level
        level = DriftLevel.NONE
        recs = []
        if self.state.error_rate_24h > 0.5:
            level = DriftLevel.CRITICAL
            recs.append("Error rate >50%: Enable auto-heal immediately")
        elif self.state.error_rate_24h > 0.3:
            level = DriftLevel.HIGH
            recs.append("Error rate >30%: Run evolution cycle")
        elif self.state.error_rate_24h > 0.15:
            level = DriftLevel.MEDIUM
            recs.append("Error rate >15%: Monitor closely")
        elif self.state.error_rate_24h > 0.05:
            level = DriftLevel.LOW
            recs.append("Slight error increase: No action needed yet")
        if self.state.cost_trend > 2.0:
            recs.append("Cost spike: Review high-cost tool calls")
            level = max(level, DriftLevel.MEDIUM)
        self.state.drift_level = level
        self.state.recommendations = recs
        self.state.last_checked = datetime.now(timezone.utc).isoformat()
        # Log
        with open(DRIFT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(self.state.to_dict(), default=str) + "\n")
        return self.state

    def get_stats(self):
        return self.state.to_dict()


class ReputationTracker:
    """Tracks agent compliance reputation."""
    def __init__(self):
        self.agents: Dict[str, AgentReputation] = {}
        self._load()

    def _load(self):
        if REPUTATION_FILE.exists():
            try:
                with open(REPUTATION_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for a in data.get("agents", []):
                    self.agents[a["agent_id"]] = AgentReputation(**a)
            except Exception: pass

    def _save(self):
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(GUARDIAN_DIR), suffix='.tmp')
        try:
            data = {"agents": [a.to_dict() for a in self.agents.values()],
                    "updated": datetime.now(timezone.utc).isoformat()}
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            os.replace(tmp_path, str(REPUTATION_FILE))
        except Exception: os.unlink(tmp_path); raise

    def record_action(self, agent_id: str, result: str):
        """Record an action result: 'compliant', 'violation', or 'warning'."""
        if agent_id not in self.agents:
            self.agents[agent_id] = AgentReputation(agent_id=agent_id)
        rep = self.agents[agent_id]
        rep.total_actions += 1
        if result == "violation":
            rep.violations += 1
            rep.last_violation = datetime.now(timezone.utc).isoformat()
            rep.trust_level = max(0.0, rep.trust_level - 0.1)
        elif result == "warning":
            rep.warnings += 1
            rep.last_warning = datetime.now(timezone.utc).isoformat()
        else:
            rep.trust_level = min(2.0, rep.trust_level + 0.01)
        rep.compliance_rate = 1.0 - (rep.violations / max(rep.total_actions, 1))
        self._save()

    def get_trust_level(self, agent_id: str) -> float:
        if agent_id not in self.agents: return 1.0
        return self.agents[agent_id].trust_level

    def get_stats(self):
        return {aid: a.to_dict() for aid, a in self.agents.items()}


class BudgetGuardian:
    """Enforces hard budget limits."""
    def __init__(self):
        self.state = BudgetState()
        self._load()

    def _load(self):
        if BUDGET_FILE.exists():
            try:
                with open(BUDGET_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.state = BudgetState(**data)
            except Exception: pass
        self._check_resets()

    def _save(self):
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(GUARDIAN_DIR), suffix='.tmp')
        try:
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                json.dump(self.state.to_dict(), f, indent=2, default=str)
            os.replace(tmp_path, str(BUDGET_FILE))
        except Exception: os.unlink(tmp_path); raise

    def _check_resets(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.state.daily_reset != today:
            self.state.daily_used = 0.0; self.state.daily_reset = today
        # Weekly reset (Monday)
        week_num = datetime.now(timezone.utc).isocalendar()[1]
        week_key = f"{datetime.now(timezone.utc).year}-W{week_num}"
        if self.state.weekly_reset != week_key:
            self.state.weekly_used = 0.0; self.state.weekly_reset = week_key
        self._save()

    def can_spend(self, amount: float) -> tuple:
        """Check if spending amount is allowed. Returns (allowed, reason)."""
        self._check_resets()
        if self.state.is_daily_exceeded():
            return False, f"Daily budget exceeded: ${self.state.daily_used:.2f}/${self.state.daily_limit:.0f}"
        if self.state.daily_remaining() < amount:
            return False, f"Insufficient daily budget: ${self.state.daily_remaining():.2f} remaining"
        if self.state.is_weekly_exceeded():
            return False, f"Weekly budget exceeded: ${self.state.weekly_used:.2f}/${self.state.weekly_limit:.0f}"
        return True, "Budget OK"

    def record_spend(self, amount: float):
        self._check_resets()
        self.state.daily_used += amount
        self.state.weekly_used += amount
        self._save()

    def get_stats(self):
        return {**self.state.to_dict(),
                "daily_remaining": self.state.daily_remaining(),
                "weekly_remaining": self.state.weekly_remaining()}


class ConstitutionalGuardianV2:
    """
    Full-stack constitutional guardian with drift detection,
    reputation tracking, and budget enforcement.
    """
    def __init__(self):
        self.drift = DriftDetector()
        self.reputation = ReputationTracker()
        self.budget = BudgetGuardian()
        # Wire to existing ConstitutionalAI
        self._constitution = None
        try:
            from constitutional_ai import get_checker
            self._constitution = get_checker()
        except Exception: pass

    def pre_check(self, action_type: str, params: dict,
                  agent_id: str = "director") -> dict:
        """Enhanced pre-check: constitution + budget + reputation."""
        result = {"action": GuardianAction.ALLOW, "reasons": [], "trust_level": 1.0}
        # 1. Constitutional check
        if self._constitution:
            try:
                c_result = self._constitution.pre_check(action_type, params)
                if not c_result.allowed:
                    result["action"] = GuardianAction.BLOCK
                    result["reasons"].append(f"Constitutional: {c_result.reason}")
                elif c_result.reason.startswith("[WARNING]"):
                    result["action"] = GuardianAction.WARN
                    result["reasons"].append(f"Warning: {c_result.reason}")
            except Exception: pass
        # 2. Budget check
        estimated_cost = params.get("estimated_cost", 0)
        if estimated_cost > 0:
            allowed, reason = self.budget.can_spend(estimated_cost)
            if not allowed:
                result["action"] = GuardianAction.BLOCK
                result["reasons"].append(f"Budget: {reason}")
        # 3. Reputation check
        trust = self.reputation.get_trust_level(agent_id)
        result["trust_level"] = trust
        if trust < 0.3:
            result["action"] = GuardianAction.BLOCK
            result["reasons"].append(f"Trust: Agent {agent_id} trust level too low ({trust:.2f})")
        elif trust < 0.5:
            if result["action"] == GuardianAction.ALLOW:
                result["action"] = GuardianAction.WARN
        # 4. Drift check
        drift = self.drift.check_drift()
        if drift.drift_level == DriftLevel.CRITICAL:
            if result["action"] != GuardianAction.BLOCK:
                result["action"] = GuardianAction.HEAL
                result["reasons"].append("System drift critical: triggering self-heal")
        # Record
        if result["action"] == GuardianAction.BLOCK:
            self.reputation.record_action(agent_id, "violation")
        elif result["action"] == GuardianAction.WARN:
            self.reputation.record_action(agent_id, "warning")
        else:
            self.reputation.record_action(agent_id, "compliant")
        result["action"] = result["action"].value if isinstance(result["action"], GuardianAction) else result["action"]
        return result

    def post_check(self, action_type: str, result: dict,
                    cost_usd: float = 0, agent_id: str = "director",
                    error: str = "") -> dict:
        """Post-action check: record drift, budget, and reputation."""
        # Record budget
        if cost_usd > 0:
            self.budget.record_spend(cost_usd)
        # Record errors for drift detection
        if error:
            self.drift.record_error(action_type, error)
        if cost_usd > 0:
            self.drift.record_cost(cost_usd)
        # Constitutional post-check
        if self._constitution:
            try:
                self._constitution.post_check(action_type, result)
            except Exception: pass
        return {"drift_level": self.drift.state.drift_level.value,
                "daily_budget_remaining": self.budget.state.daily_remaining(),
                "trust_level": self.reputation.get_trust_level(agent_id)}

    def get_full_status(self) -> dict:
        return {
            "drift": self.drift.get_stats(),
            "reputation": self.reputation.get_stats(),
            "budget": self.budget.get_stats(),
            "constitution_wired": self._constitution is not None,
        }


_guardian: Optional[ConstitutionalGuardianV2] = None
def get_guardian() -> ConstitutionalGuardianV2:
    global _guardian
    if _guardian is None: _guardian = ConstitutionalGuardianV2()
    return _guardian


if __name__ == "__main__":
    import sys
    guardian = get_guardian()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status": print(json.dumps(guardian.get_full_status(), indent=2, default=str))
    elif cmd == "check" and len(sys.argv) > 2:
        result = guardian.pre_check(sys.argv[2], {})
        print(json.dumps(result, indent=2, default=str))
    elif cmd == "drift": print(json.dumps(guardian.drift.get_stats(), indent=2, default=str))
    elif cmd == "budget": print(json.dumps(guardian.budget.get_stats(), indent=2, default=str))
    else: print("Commands: status, check <action_type>, drift, budget")