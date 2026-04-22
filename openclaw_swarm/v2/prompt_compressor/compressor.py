"""
Prompt Compression System — Inspired by OpenClaude autoCompact + microCompact.
Compresses conversation context to fit within context windows while preserving
critical information.

Strategies:
1. Snip Compact: Remove low-value messages (greetings, acknowledgments)
2. Micro Compact: Replace tool outputs with summaries
3. Time-based Compact: Compress old messages into summaries
4. Semantic Compact: Deduplicate similar messages, keep most informative
5. Priority Compact: Keep recent + important + error messages, drop rest

Inspired by:
- OpenClaude: compact.ts, snipCompact.ts, sessionMemoryCompact.ts
- Plandex: 2M token context management with selective loading
"""

import json
import os
import re
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

BASE_DIR = Path(
    os.environ.get(
        "OPENCLAW_DIRECTOR_DIR", Path.home() / ".openclaw" / "workspaces" / "director"
    )
)
COMPACT_DIR = BASE_DIR / "prompt_compressor"
COMPACT_DIR.mkdir(parents=True, exist_ok=True)
COMPACT_LOG = COMPACT_DIR / "compact_log.jsonl"


class CompactStrategy(str, Enum):
    SNIP = "snip"  # Remove low-value messages
    MICRO = "micro"  # Summary of tool outputs
    TIME = "time"  # Compress old messages
    SEMANTIC = "semantic"  # Deduplicate similar messages
    PRIORITY = "priority"  # Keep important only


@dataclass
class CompactMessage:
    """A message in the conversation being compressed."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: str = ""
    token_count: int = 0
    importance: float = 0.5  # 0.0-1.0
    category: str = (
        "general"  # "greeting", "acknowledgment", "tool_output", "error", "question", "answer", "code", "reasoning"
    )
    is_compressed: bool = False
    original_length: int = 0

    def to_dict(self):
        return asdict(self)


@dataclass
class CompactResult:
    """Result of a compression operation."""

    strategy: CompactStrategy
    original_messages: int = 0
    compressed_messages: int = 0
    original_tokens: int = 0
    compressed_tokens: int = 0
    savings_pct: float = 0.0
    duration_ms: int = 0

    def to_dict(self):
        return {**asdict(self), "strategy": self.strategy.value}


class MessageClassifier:
    """Classifies conversation messages by type and importance."""

    GREETING_PATTERNS = [
        r"^(hi|hello|hey|thanks|thank you|ok|okay|got it|understood|sure|yes|no)\s*[.!]?$",
        r"^(أهلا|مرحبا|شكرا|تمام|فهمت|تم|أوكي|نعم|لا)\s*[.!]?$",
    ]
    ACK_PATTERNS = [
        r"^(done|completed|finished|processed|applied|updated|created|deleted)\b",
        r"^(I|we|the system)?\s*(have|has|will|can|did)\s+(updated|applied|created|completed|fixed)",
    ]
    ERROR_PATTERNS = [
        r"\b(error|exception|failed|failure|traceback|bug|crash)\b",
        r"\b(خطأ|استثناء|فشل|عطل)\b",
    ]
    CODE_PATTERNS = [
        r"```",
        r"def |class |import |function |const |var |let ",
        r"if __name__",
        r"return\s",
    ]
    QUESTION_PATTERNS = [
        r"\?{2,}",
        r"^(what|how|why|when|where|who|which|can you|could you)",
        r"^(إيه|إزاي|ليه|متى|فيين|مين|أنهي)",
    ]

    def classify(self, msg: CompactMessage) -> Tuple[str, float]:
        """Return (category, importance) for a message."""
        content = msg.content.strip()
        if not content:
            return "empty", 0.0

        lower = content.lower()

        # Check patterns
        for pat in self.GREETING_PATTERNS:
            if re.match(pat, lower):
                return "greeting", 0.1

        for pat in self.ACK_PATTERNS:
            if re.search(pat, lower):
                return "acknowledgment", 0.2

        for pat in self.ERROR_PATTERNS:
            if re.search(pat, lower):
                return "error", 0.9

        for pat in self.CODE_PATTERNS:
            if re.search(pat, content):
                return "code", 0.8

        for pat in self.QUESTION_PATTERNS:
            if re.search(pat, lower):
                return "question", 0.7

        # Heuristics
        if msg.role == "system":
            return "system", 0.9
        elif msg.role == "tool":
            if len(content) > 500:
                return "tool_output", 0.3  # Long tool outputs less important
            return "tool_output", 0.5
        elif msg.role == "assistant":
            if any(kw in lower for kw in ["plan", "architect", "design", "decision"]):
                return "reasoning", 0.8
            return "answer", 0.6
        elif msg.role == "user":
            return "question", 0.7

        return "general", 0.5

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: 1 token ~ 4 chars)."""
        return max(1, len(text) // 4)


class PromptCompressor:
    """
    Compresses conversation context using multiple strategies.
    """

    def __init__(self):
        self.classifier = MessageClassifier()

    def classify_messages(self, messages: List[dict]) -> List[CompactMessage]:
        """Convert raw messages to classified CompactMessages."""
        result = []
        for msg in messages:
            cm = CompactMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp", ""),
            )
            category, importance = self.classifier.classify(cm)
            cm.category = category
            cm.importance = importance
            cm.token_count = self.classifier.estimate_tokens(cm.content)
            cm.original_length = len(cm.content)
            result.append(cm)
        return result

    def compact_snip(
        self, messages: List[CompactMessage], min_importance: float = 0.3
    ) -> Tuple[List[CompactMessage], CompactResult]:
        """Strategy 1: Remove low-value messages (greetings, acks, empty)."""
        start = time.time()
        original_count = len(messages)
        original_tokens = sum(m.token_count for m in messages)

        kept = [m for m in messages if m.importance >= min_importance]

        compressed_tokens = sum(m.token_count for m in kept)
        result = CompactResult(
            strategy=CompactStrategy.SNIP,
            original_messages=original_count,
            compressed_messages=len(kept),
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            savings_pct=round(
                (1 - compressed_tokens / max(original_tokens, 1)) * 100, 1
            ),
            duration_ms=int((time.time() - start) * 1000),
        )
        return kept, result

    def compact_micro(
        self, messages: List[CompactMessage], max_tool_output_tokens: int = 50
    ) -> Tuple[List[CompactMessage], CompactResult]:
        """Strategy 2: Replace long tool outputs with short summaries."""
        start = time.time()
        original_tokens = sum(m.token_count for m in messages)
        result_msgs = []

        for m in messages:
            if m.category == "tool_output" and m.token_count > max_tool_output_tokens:
                # Create a micro summary
                summary = m.content[:200] + "...[compressed]"
                cm = CompactMessage(
                    role=m.role,
                    content=summary,
                    timestamp=m.timestamp,
                    token_count=max_tool_output_tokens,
                    importance=m.importance,
                    category=m.category,
                    is_compressed=True,
                    original_length=m.original_length,
                )
                result_msgs.append(cm)
            else:
                result_msgs.append(m)

        compressed_tokens = sum(m.token_count for m in result_msgs)
        result = CompactResult(
            strategy=CompactStrategy.MICRO,
            original_messages=len(messages),
            compressed_messages=len(result_msgs),
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            savings_pct=round(
                (1 - compressed_tokens / max(original_tokens, 1)) * 100, 1
            ),
            duration_ms=int((time.time() - start) * 1000),
        )
        return result_msgs, result

    def compact_time(
        self,
        messages: List[CompactMessage],
        recent_keep_count: int = 10,
        summary_max_tokens: int = 200,
    ) -> Tuple[List[CompactMessage], CompactResult]:
        """Strategy 3: Compress old messages into a single summary."""
        start = time.time()
        original_tokens = sum(m.token_count for m in messages)

        if len(messages) <= recent_keep_count:
            return messages, CompactResult(
                strategy=CompactStrategy.TIME,
                original_messages=len(messages),
                compressed_messages=len(messages),
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
            )

        # Keep recent messages as-is
        recent = messages[-recent_keep_count:]
        older = messages[:-recent_keep_count]

        # Create summary of older messages
        summary_parts = []
        for m in older:
            if m.importance >= 0.5:
                summary_parts.append(f"[{m.role}] {m.content[:100]}")

        summary_text = "[Earlier conversation summary]\n" + "\n".join(
            summary_parts[-10:]
        )
        summary = CompactMessage(
            role="system",
            content=summary_text,
            timestamp=older[-1].timestamp if older else "",
            token_count=self.classifier.estimate_tokens(summary_text),
            importance=0.9,
            category="summary",
            is_compressed=True,
            original_length=sum(m.original_length for m in older),
        )

        result_msgs = [summary] + recent
        compressed_tokens = sum(m.token_count for m in result_msgs)
        result = CompactResult(
            strategy=CompactStrategy.TIME,
            original_messages=len(messages),
            compressed_messages=len(result_msgs),
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            savings_pct=round(
                (1 - compressed_tokens / max(original_tokens, 1)) * 100, 1
            ),
            duration_ms=int((time.time() - start) * 1000),
        )
        return result_msgs, result

    def compact_priority(
        self, messages: List[CompactMessage], max_tokens: int = 50000
    ) -> Tuple[List[CompactMessage], CompactResult]:
        """Strategy 4: Keep messages by priority until budget exhausted."""
        start = time.time()
        original_tokens = sum(m.token_count for m in messages)

        # Sort by importance (keep system messages first, then by importance)
        priority_order = {
            "system": 0,
            "error": 1,
            "reasoning": 2,
            "code": 3,
            "question": 4,
            "answer": 5,
            "tool_output": 6,
            "acknowledgment": 7,
            "greeting": 8,
            "empty": 9,
        }
        sorted_msgs = sorted(
            messages, key=lambda m: (priority_order.get(m.category, 5), -m.importance)
        )

        kept = []
        token_budget = max_tokens
        for m in sorted_msgs:
            if m.token_count <= token_budget:
                kept.append(m)
                token_budget -= m.token_count

        # Restore original order
        kept_set = {id(m) for m in kept}
        ordered = [m for m in messages if id(m) in kept_set]

        compressed_tokens = sum(m.token_count for m in ordered)
        result = CompactResult(
            strategy=CompactStrategy.PRIORITY,
            original_messages=len(messages),
            compressed_messages=len(ordered),
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            savings_pct=round(
                (1 - compressed_tokens / max(original_tokens, 1)) * 100, 1
            ),
            duration_ms=int((time.time() - start) * 1000),
        )
        return ordered, result

    def auto_compact(
        self, messages: List[dict], target_tokens: int = 100000
    ) -> Tuple[List[dict], dict]:
        """
        Automatically choose the best compression strategy.
        Returns (compressed_messages, report).
        """
        classified = self.classify_messages(messages)
        total_tokens = sum(m.token_count for m in classified)

        if total_tokens <= target_tokens:
            return messages, {
                "strategy": "none",
                "reason": "within budget",
                "original_tokens": total_tokens,
            }

        # Calculate how much savings we need
        (total_tokens - target_tokens) / total_tokens

        # Try strategies in order of aggressiveness
        results = []
        for strategy_fn, strategy_name in [
            (self.compact_snip, "snip"),
            (self.compact_micro, "micro"),
            (self.compact_time, "time"),
            (self.compact_priority, "priority"),
        ]:
            compressed, result = strategy_fn(classified)
            results.append((compressed, result))

        # Pick the strategy that gets closest to target without going under
        best = None
        for compressed, result in results:
            if result.compressed_tokens <= target_tokens:
                if best is None or result.compressed_tokens > best[1].compressed_tokens:
                    best = (compressed, result)

        if best is None:
            # Use most aggressive
            best = min(results, key=lambda x: x[1].compressed_tokens)

        # Convert back to raw messages
        output = [
            {"role": m.role, "content": m.content, "compressed": m.is_compressed}
            for m in best[0]
        ]

        report = best[1].to_dict()
        report["auto_selected"] = True

        # Log
        with open(COMPACT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(report, default=str) + "\n")

        return output, report

    def get_stats(self) -> dict:
        entries = []
        if COMPACT_LOG.exists():
            with open(COMPACT_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entries.append(json.loads(line.strip()))
                    except Exception:
                        pass
        return {
            "total_compacts": len(entries),
            "avg_savings_pct": round(
                sum(e.get("savings_pct", 0) for e in entries) / max(len(entries), 1), 1
            ),
            "strategies_used": {
                s: sum(1 for e in entries if e.get("strategy") == s)
                for s in set(e.get("strategy", "") for e in entries)
            },
        }


_compressor: Optional[PromptCompressor] = None


def get_compressor() -> PromptCompressor:
    global _compressor
    if _compressor is None:
        _compressor = PromptCompressor()
    return _compressor


if __name__ == "__main__":

    comp = get_compressor()
    # Demo: classify and compress sample messages
    sample = [
        {"role": "user", "content": "Hi there!"},
        {"role": "assistant", "content": "Hello! How can I help?"},
        {
            "role": "user",
            "content": "Fix the bug in auth.py - the login function throws a KeyError",
        },
        {
            "role": "assistant",
            "content": "I'll analyze the auth.py file and fix the KeyError in the login function.",
        },
        {
            "role": "tool",
            "content": "File auth.py (500 lines):\n"
            + "def login(user, pwd):\n    return db[user]\n" * 100,
        },
        {
            "role": "assistant",
            "content": "The issue is on line 23 - db[user] throws KeyError when user not found. I'll add a .get() check.",
        },
        {
            "role": "assistant",
            "content": "Fixed: replaced `return db[user]` with `return db.get(user, None)`",
        },
        {"role": "user", "content": "Thanks!"},
        {"role": "assistant", "content": "You're welcome!"},
    ]
    classified = comp.classify_messages(sample)
    print("=== Classified Messages ===")
    for m in classified:
        print(
            f"  [{m.category:15s}] imp={m.importance:.1f} tok={m.token_count:4d} | {m.content[:40]}"
        )
    print()
    compressed, report = comp.auto_compact(sample, target_tokens=200)
    print("=== Auto Compact ===")
    print(f"Strategy: {report.get('strategy', 'none')}")
    print(
        f"Messages: {report.get('original_messages', 0)} -> {report.get('compressed_messages', 0)}"
    )
    print(
        f"Tokens: {report.get('original_tokens', 0)} -> {report.get('compressed_tokens', 0)} ({report.get('savings_pct', 0)}% savings)"
    )
