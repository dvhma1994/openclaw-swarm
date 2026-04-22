"""
Streaming Token Counter — Inspired by OpenClaude Issues #795-800.
Real-time token counting with:
- Per-model tokenizer estimation
- Streaming token counting (incremental)
- Token budget calculator
- Error-bound estimation
- Compression ratio detection
- Cache hit tracking for prompt caching
- Cross-session token cache
"""

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

BASE_DIR = Path(
    os.environ.get(
        "OPENCLAW_DIRECTOR_DIR", Path.home() / ".openclaw" / "workspaces" / "director"
    )
)
TOKEN_DIR = BASE_DIR / "streaming_token_counter"
TOKEN_DIR.mkdir(parents=True, exist_ok=True)
TOKEN_CACHE = TOKEN_DIR / "token_cache.json"


# Model-specific tokenizer ratios (tokens per character, approximate)
MODEL_RATIOS = {
    "default": {"input": 0.25, "output": 0.25},  # ~4 chars per token
    "gpt-4": {"input": 0.25, "output": 0.25},
    "gpt-4o": {"input": 0.25, "output": 0.25},
    "claude": {"input": 0.22, "output": 0.22},  # Claude slightly more efficient
    "sonnet": {"input": 0.22, "output": 0.22},
    "haiku": {"input": 0.22, "output": 0.22},
    "opus": {"input": 0.22, "output": 0.22},
    "gemini": {"input": 0.25, "output": 0.25},
    "deepseek": {"input": 0.28, "output": 0.28},
    "llama": {"input": 0.27, "output": 0.27},
    "qwen": {"input": 0.30, "output": 0.30},  # CJK models
}

# Pricing per 1M tokens (input/output in USD)
MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "sonnet": {"input": 3.00, "output": 15.00},
    "haiku": {"input": 0.25, "output": 1.25},
    "opus": {"input": 15.0, "output": 75.0},
    "gemini-pro": {"input": 1.25, "output": 5.00},
    "deepseek": {"input": 0.27, "output": 1.10},
}


@dataclass
class TokenCount:
    """Token count result."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_chars: int = 0
    output_chars: int = 0
    model: str = "default"
    confidence: float = 0.8  # How accurate the count is (1.0 = exact)
    cached_tokens: int = 0  # Tokens served from cache

    def to_dict(self):
        return asdict(self)


@dataclass
class TokenBudget:
    """Token budget status."""

    total_budget: int = 200000
    used: int = 0
    remaining: int = 0
    usage_pct: float = 0.0
    projected_completion: bool = True  # Can the task complete within budget?
    estimated_remaining_turns: int = 0
    cost_usd: float = 0.0
    cost_remaining_usd: float = 0.0

    def to_dict(self):
        return asdict(self)


@dataclass
class CacheEntry:
    """A cached token count for a content hash."""

    content_hash: str
    token_count: int
    model: str = ""
    created_at: str = ""
    hit_count: int = 0


class StreamingTokenCounter:
    """
    Real-time token counting with models, budgeting, and caching.
    """

    def __init__(self):
        self._counts: Dict[str, TokenCount] = {}  # session_id -> count
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._load_cache()

    def _load_cache(self):
        if TOKEN_CACHE.exists():
            try:
                with open(TOKEN_CACHE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for entry in data.get("entries", []):
                    ce = CacheEntry(**entry)
                    self._cache[ce.content_hash] = ce
            except Exception:
                pass

    def _save_cache(self):
        data = {
            "entries": [ce.__dict__ for ce in list(self._cache.values())[-500:]],
            "updated": datetime.now(timezone.utc).isoformat(),
        }
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(TOKEN_DIR), suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, str(TOKEN_CACHE))
        except Exception:
            os.unlink(tmp_path)
            raise

    def count_tokens(
        self, text: str, model: str = "default", is_input: bool = True
    ) -> int:
        """Estimate token count for a text using model-specific ratios."""
        if not text:
            return 0
        # Check cache first
        content_hash = hashlib.md5(text.encode()).hexdigest()
        cache_key = f"{content_hash}_{model}"
        with self._lock:
            if cache_key in self._cache:
                ce = self._cache[cache_key]
                ce.hit_count += 1
                return ce.token_count

        # Model-specific estimation
        ratios = MODEL_RATIOS.get(model, MODEL_RATIOS["default"])
        ratio = ratios["input"] if is_input else ratios["output"]

        # Better estimation: consider whitespace, code patterns
        tokens = 0
        # Code patterns (more tokens per char due to punctuation)
        code_chars = sum(1 for c in text if c in "{}[]()=;:<>,./\\!@#$%^&*")
        text_chars = len(text) - code_chars
        tokens = int(text_chars * ratio + code_chars * ratio * 1.3)

        # Cache the result
        with self._lock:
            self._cache[cache_key] = CacheEntry(
                content_hash=cache_key,
                token_count=tokens,
                model=model,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            # Periodic save
            if len(self._cache) % 50 == 0:
                self._save_cache()

        return max(1, tokens)

    def count_streaming(self, text_chunks: list, model: str = "default") -> TokenCount:
        """Count tokens from a streaming response (list of chunks)."""
        total_input = 0
        total_output = 0
        for i, chunk in enumerate(text_chunks):
            if i == 0:
                total_input += self.count_tokens(str(chunk), model, is_input=True)
            else:
                total_output += self.count_tokens(str(chunk), model, is_input=False)
        return TokenCount(
            input_tokens=total_input,
            output_tokens=total_output,
            total_tokens=total_input + total_output,
            model=model,
            confidence=0.85,
        )

    def calculate_budget(
        self,
        session_id: str,
        model: str = "sonnet",
        daily_budget_usd: float = 10.0,
        context_window: int = 200000,
    ) -> TokenBudget:
        """Calculate token budget status for a session."""
        count = self._counts.get(session_id, TokenCount(model=model))
        used = count.total_tokens
        pricing = MODEL_PRICING.get(model, {"input": 3.0, "output": 15.0})

        # Cost calculation
        input_cost = (count.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (count.output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        remaining = max(0, context_window - used)
        usage_pct = (used / max(context_window, 1)) * 100

        # Estimate remaining turns (rough: avg 2000 tokens/turn)
        avg_turn_tokens = 2000
        remaining_turns = remaining // avg_turn_tokens if avg_turn_tokens > 0 else 0

        # Budget in USD
        remaining_usd = max(0, daily_budget_usd - total_cost)
        can_complete = remaining > avg_turn_tokens * 3 and remaining_usd > 0.1

        return TokenBudget(
            total_budget=context_window,
            used=used,
            remaining=remaining,
            usage_pct=round(usage_pct, 1),
            projected_completion=can_complete,
            estimated_remaining_turns=remaining_turns,
            cost_usd=round(total_cost, 4),
            cost_remaining_usd=round(remaining_usd, 4),
        )

    def record_usage(
        self,
        session_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model: str = "default",
        cached_tokens: int = 0,
    ):
        """Record token usage for a session."""
        if session_id not in self._counts:
            self._counts[session_id] = TokenCount(model=model)
        count = self._counts[session_id]
        count.input_tokens += input_tokens
        count.output_tokens += output_tokens
        count.total_tokens = count.input_tokens + count.output_tokens
        count.cached_tokens += cached_tokens

    def get_compression_ratio(self, original: str, compressed: str) -> float:
        """Calculate token compression ratio."""
        orig_tokens = self.count_tokens(original)
        comp_tokens = self.count_tokens(compressed)
        if orig_tokens == 0:
            return 1.0
        return round(comp_tokens / orig_tokens, 3)

    def estimate_error_bound(self, text: str, model: str = "default") -> dict:
        """Estimate error bounds for token counting."""
        count = self.count_tokens(text, model)
        # Heuristic: longer text = more error
        error_pct = min(15, 3 + len(text) / 1000)
        return {
            "estimated_tokens": count,
            "error_bound_pct": error_pct,
            "min_tokens": int(count * (1 - error_pct / 100)),
            "max_tokens": int(count * (1 + error_pct / 100)),
            "confidence": 1 - error_pct / 100,
            "model": model,
        }

    def get_stats(self) -> dict:
        return {
            "active_sessions": len(self._counts),
            "total_tokens_tracked": sum(c.total_tokens for c in self._counts.values()),
            "cache_entries": len(self._cache),
            "cache_hits": sum(ce.hit_count for ce in self._cache.values()),
            "supported_models": list(MODEL_RATIOS.keys()),
            "priced_models": list(MODEL_PRICING.keys()),
        }


_counter: Optional[StreamingTokenCounter] = None


def get_token_counter() -> StreamingTokenCounter:
    global _counter
    if _counter is None:
        _counter = StreamingTokenCounter()
    return _counter


if __name__ == "__main__":
    import sys

    counter = get_token_counter()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        print(json.dumps(counter.get_stats(), indent=2))
    elif cmd == "count" and len(sys.argv) > 2:
        model = sys.argv[3] if len(sys.argv) > 3 else "sonnet"
        tokens = counter.count_tokens(sys.argv[2], model)
        print(f"Estimated tokens: {tokens} (model: {model})")
    elif cmd == "budget" and len(sys.argv) > 2:
        budget = counter.calculate_budget(sys.argv[2])
        print(json.dumps(budget.to_dict(), indent=2))
    elif cmd == "error" and len(sys.argv) > 2:
        result = counter.estimate_error_bound(sys.argv[2])
        print(json.dumps(result, indent=2))
    else:
        print(
            "Commands: stats, count <text> [model], budget <session_id>, error <text>"
        )
