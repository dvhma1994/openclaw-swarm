"""
Multi-tier Memory System
Working + Episodic + Semantic Memory
Inspired by: human memory architecture
"""

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
import logging

console = Console()


class MemoryTier(Enum):
    """Memory tiers"""

    WORKING = "working"  # Short-term, limited capacity, current task
    EPISODIC = "episodic"  # Medium-term, events and experiences
    SEMANTIC = "semantic"  # Long-term, compressed knowledge


@dataclass
class WorkingMemoryItem:
    """Working memory item - current context"""

    id: str
    content: str
    timestamp: str
    priority: int  # 1-10, higher = more important
    access_count: int = 0
    last_access: str = ""

    def touch(self):
        """Update access"""
        self.access_count += 1
        self.last_access = datetime.now().isoformat()


@dataclass
class EpisodicMemoryItem:
    """Episodic memory item - events and experiences"""

    id: str
    event: str
    timestamp: str
    participants: List[str]
    context: str
    outcome: str
    emotional_valence: float  # -1 to 1 (negative to positive)
    importance: float  # 0 to 1
    tags: List[str] = field(default_factory=list)


@dataclass
class SemanticMemoryItem:
    """Semantic memory item - compressed knowledge"""

    id: str
    concept: str
    knowledge: str
    source_ids: List[str]  # IDs of episodic memories this came from
    confidence: float  # 0 to 1
    last_updated: str
    use_count: int = 0


class WorkingMemory:
    """
    Working Memory - Short-term, limited capacity

    Characteristics:
    - Holds 7±2 items at once (Miller's law)
    - Current task context
    - Fast access
    - Auto-forgets after timeout or capacity exceeded
    """

    CAPACITY = 7  # Miller's law
    TIMEOUT_MINUTES = 30

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(
            storage_path
            or os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "memory", "working"
            )
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.items: Dict[str, WorkingMemoryItem] = {}
        self._load()

    def _load(self) -> None:
        """Load from disk"""
        file = self.storage_path / "working.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.items = {k: WorkingMemoryItem(**v) for k, v in data.items()}
            except Exception:
                logging.warning("Failed to load working memory", exc_info=True)

    def _save(self) -> None:
        """Save to disk"""
        file = self.storage_path / "working.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump(
                {k: asdict(v) for k, v in self.items.items()},
                f,
                indent=2,
                ensure_ascii=False,
            )

    def _generate_id(self, content: str) -> str:
        return hashlib.md5(
            f"{content}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

    def add(self, content: str, priority: int = 5) -> str:
        """Add item to working memory"""
        # Check capacity
        if len(self.items) >= self.CAPACITY:
            self._evict_lowest_priority()

        item_id = self._generate_id(content)

        item = WorkingMemoryItem(
            id=item_id,
            content=content,
            timestamp=datetime.now().isoformat(),
            priority=max(1, min(10, priority)),
        )

        self.items[item_id] = item
        self._save()

        return item_id

    def get(self, item_id: str) -> Optional[str]:
        """Get item content"""
        if item_id in self.items:
            self.items[item_id].touch()
            self._save()
            return self.items[item_id].content
        return None

    def get_all(self) -> List[WorkingMemoryItem]:
        """Get all items sorted by priority"""
        return sorted(self.items.values(), key=lambda x: x.priority, reverse=True)

    def clear(self) -> None:
        """Clear all items"""
        self.items.clear()
        self._save()

    def _evict_lowest_priority(self) -> None:
        """Evict lowest priority item"""
        if not self.items:
            return

        # Find lowest priority, oldest accessed
        lowest = min(self.items.values(), key=lambda x: (x.priority, x.access_count))
        del self.items[lowest.id]

    def cleanup_expired(self) -> int:
        """Remove expired items"""
        cutoff = datetime.now() - timedelta(minutes=self.TIMEOUT_MINUTES)

        to_remove = []
        for item_id, item in self.items.items():
            item_time = datetime.fromisoformat(item.timestamp)
            if item_time < cutoff:
                to_remove.append(item_id)

        for item_id in to_remove:
            del self.items[item_id]

        self._save()
        return len(to_remove)

    def promote_to_episodic(self, item_id: str) -> Optional[WorkingMemoryItem]:
        """Promote item to episodic memory"""
        if item_id in self.items:
            return self.items[item_id]
        return None


class EpisodicMemory:
    """
    Episodic Memory - Medium-term, events and experiences

    Characteristics:
    - Stores events with context
    - Emotional tagging
    - Importance scoring
    - Compressed after time
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(
            storage_path
            or os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "memory", "episodic"
            )
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.items: Dict[str, EpisodicMemoryItem] = {}
        self._load()

    def _load(self) -> None:
        """Load from disk"""
        file = self.storage_path / "episodic.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.items = {k: EpisodicMemoryItem(**v) for k, v in data.items()}
            except Exception:
                logging.warning("Failed to load episodic memory", exc_info=True)

    def _save(self) -> None:
        """Save to disk"""
        file = self.storage_path / "episodic.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump(
                {k: asdict(v) for k, v in self.items.items()},
                f,
                indent=2,
                ensure_ascii=False,
            )

    def _generate_id(self, event: str) -> str:
        return hashlib.md5(
            f"{event}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

    def store(
        self,
        event: str,
        participants: List[str],
        context: str,
        outcome: str,
        emotional_valence: float = 0.0,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Store an episodic memory"""
        item_id = self._generate_id(event)

        item = EpisodicMemoryItem(
            id=item_id,
            event=event,
            timestamp=datetime.now().isoformat(),
            participants=participants,
            context=context,
            outcome=outcome,
            emotional_valence=max(-1, min(1, emotional_valence)),
            importance=max(0, min(1, importance)),
            tags=tags or [],
        )

        self.items[item_id] = item
        self._save()

        return item_id

    def get(self, item_id: str) -> Optional[EpisodicMemoryItem]:
        """Get specific memory"""
        return self.items.get(item_id)

    def search(
        self,
        query: Optional[str] = None,
        participants: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        min_importance: float = 0.0,
        limit: int = 10,
    ) -> List[EpisodicMemoryItem]:
        """Search episodic memories"""
        results = list(self.items.values())

        # Filter by query
        if query:
            query_lower = query.lower()
            results = [
                r
                for r in results
                if query_lower in r.event.lower()
                or query_lower in r.context.lower()
                or query_lower in r.outcome.lower()
            ]

        # Filter by participants
        if participants and isinstance(participants, list):
            results = [
                r for r in results if any(p in r.participants for p in participants)
            ]

        # Filter by tags
        if tags and isinstance(tags, list):
            results = [r for r in results if any(t in r.tags for t in tags)]

        # Filter by importance
        results = [r for r in results if r.importance >= min_importance]

        # Sort by importance and timestamp
        results.sort(key=lambda x: (x.importance, x.timestamp), reverse=True)

        return results[:limit]

    def get_recent(self, hours: int = 24, limit: int = 10) -> List[EpisodicMemoryItem]:
        """Get recent memories"""
        cutoff = datetime.now() - timedelta(hours=hours)

        recent = [
            item
            for item in self.items.values()
            if datetime.fromisoformat(item.timestamp) > cutoff
        ]

        recent.sort(key=lambda x: x.timestamp, reverse=True)

        return recent[:limit]

    def get_important(
        self, min_importance: float = 0.7, limit: int = 10
    ) -> List[EpisodicMemoryItem]:
        """Get important memories"""
        important = [
            item for item in self.items.values() if item.importance >= min_importance
        ]

        important.sort(key=lambda x: x.importance, reverse=True)

        return important[:limit]

    def compress_to_semantic(self) -> List[Dict[str, Any]]:
        """Compress episodic memories to semantic knowledge"""
        # Group by tags
        tag_groups: Dict[str, List[EpisodicMemoryItem]] = {}

        for item in self.items.values():
            for tag in item.tags:
                if tag not in tag_groups:
                    tag_groups[tag] = []
                tag_groups[tag].append(item)

        # Create semantic knowledge for each group
        semantic_items = []

        for tag, items in tag_groups.items():
            if len(items) < 2:
                continue

            # Combine outcomes
            success_count = sum(1 for i in items if i.emotional_valence > 0)
            total = len(items)

            knowledge = {
                "concept": tag,
                "knowledge": f"Based on {total} experiences: {success_count/total*100:.0f}% success rate",
                "source_ids": [i.id for i in items],
                "confidence": min(
                    1.0, total / 10
                ),  # More experiences = higher confidence
            }

            semantic_items.append(knowledge)

        return semantic_items


class SemanticMemory:
    """
    Semantic Memory - Long-term, compressed knowledge

    Characteristics:
    - Compressed facts
    - High-level concepts
    - Confidence scoring
    - Slow to update
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(
            storage_path
            or os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "memory", "semantic"
            )
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.items: Dict[str, SemanticMemoryItem] = {}
        self._load()

    def _load(self) -> None:
        """Load from disk"""
        file = self.storage_path / "semantic.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.items = {k: SemanticMemoryItem(**v) for k, v in data.items()}
            except Exception:
                logging.warning("Failed to load semantic memory", exc_info=True)

    def _save(self) -> None:
        """Save to disk"""
        file = self.storage_path / "semantic.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump(
                {k: asdict(v) for k, v in self.items.items()},
                f,
                indent=2,
                ensure_ascii=False,
            )

    def store(
        self,
        concept: str,
        knowledge: str,
        source_ids: List[str],
        confidence: float = 0.5,
    ) -> str:
        """Store semantic knowledge"""
        # Check if concept exists
        existing = self.find_concept(concept)

        if existing:
            # Update existing
            existing.knowledge = knowledge
            existing.source_ids.extend(source_ids)
            existing.confidence = min(1.0, existing.confidence + 0.1)
            existing.last_updated = datetime.now().isoformat()
            existing.use_count += 1
            self._save()
            return existing.id

        # Create new
        item_id = hashlib.md5(concept.encode()).hexdigest()[:8]

        item = SemanticMemoryItem(
            id=item_id,
            concept=concept,
            knowledge=knowledge,
            source_ids=source_ids,
            confidence=confidence,
            last_updated=datetime.now().isoformat(),
        )

        self.items[item_id] = item
        self._save()

        return item_id

    def get(self, item_id: str) -> Optional[SemanticMemoryItem]:
        """Get specific knowledge"""
        if item_id in self.items:
            self.items[item_id].use_count += 1
            self._save()
            return self.items[item_id]
        return None

    def find_concept(self, concept: str) -> Optional[SemanticMemoryItem]:
        """Find knowledge by concept"""
        for item in self.items.values():
            if item.concept.lower() == concept.lower():
                return item
        return None

    def search(self, query: str, limit: int = 10) -> List[SemanticMemoryItem]:
        """Search knowledge"""
        query_lower = query.lower()

        results = [
            item
            for item in self.items.values()
            if query_lower in item.concept.lower()
            or query_lower in item.knowledge.lower()
        ]

        # Sort by confidence and use count
        results.sort(key=lambda x: (x.confidence, x.use_count), reverse=True)

        return results[:limit]

    def get_high_confidence(
        self, min_confidence: float = 0.8, limit: int = 10
    ) -> List[SemanticMemoryItem]:
        """Get high confidence knowledge"""
        results = [
            item for item in self.items.values() if item.confidence >= min_confidence
        ]

        results.sort(key=lambda x: x.confidence, reverse=True)

        return results[:limit]


class MultiTierMemory:
    """
    Complete Multi-tier Memory System

    Combines:
    - Working Memory (short-term)
    - Episodic Memory (medium-term)
    - Semantic Memory (long-term)

    With automatic promotion and compression
    """

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(
            base_path
            or os.path.join(os.path.dirname(__file__), "..", "..", "data", "memory")
        )

        self.working = WorkingMemory(str(self.base_path / "working"))
        self.episodic = EpisodicMemory(str(self.base_path / "episodic"))
        self.semantic = SemanticMemory(str(self.base_path / "semantic"))

        # Auto-compression interval
        self.last_compression = datetime.now()
        self.compression_interval_hours = 24

    def add_to_working(self, content: str, priority: int = 5) -> str:
        """Add to working memory"""
        return self.working.add(content, priority)

    def store_event(
        self,
        event: str,
        participants: List[str],
        context: str,
        outcome: str,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Store an event in episodic memory"""
        emotional = (
            1.0
            if "success" in outcome.lower()
            else (-1.0 if "fail" in outcome.lower() else 0.0)
        )

        return self.episodic.store(
            event=event,
            participants=participants,
            context=context,
            outcome=outcome,
            emotional_valence=emotional,
            importance=importance,
            tags=tags,
        )

    def promote_working_to_episodic(self, item_id: str) -> bool:
        """Promote working memory to episodic"""
        item = self.working.promote_to_episodic(item_id)

        if item:
            self.episodic.store(
                event=item.content,
                participants=["system"],
                context="Promoted from working memory",
                outcome="Stored in episodic",
                importance=item.priority / 10,
            )

            del self.working.items[item_id]
            self.working._save()
            return True

        return False

    def run_compression(self) -> Dict[str, int]:
        """Run compression from episodic to semantic"""
        semantic_items = self.episodic.compress_to_semantic()

        count = 0
        for item in semantic_items:
            self.semantic.store(
                concept=item["concept"],
                knowledge=item["knowledge"],
                source_ids=item["source_ids"],
                confidence=item["confidence"],
            )
            count += 1

        self.last_compression = datetime.now()

        return {"compressed": count}

    def recall(self, query: str, limit: int = 5) -> Dict[str, List[Any]]:
        """Recall from all tiers"""
        return {
            "working": [
                {"content": item.content, "priority": item.priority}
                for item in self.working.get_all()[:limit]
            ],
            "episodic": [
                {
                    "event": item.event,
                    "outcome": item.outcome,
                    "importance": item.importance,
                }
                for item in self.episodic.search(query, limit)
            ],
            "semantic": [
                {
                    "concept": item.concept,
                    "knowledge": item.knowledge,
                    "confidence": item.confidence,
                }
                for item in self.semantic.search(query, limit)
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return {
            "working": {
                "count": len(self.working.items),
                "capacity": self.working.CAPACITY,
                "utilization": len(self.working.items) / self.working.CAPACITY,
            },
            "episodic": {
                "count": len(self.episodic.items),
                "important": len(self.episodic.get_important()),
                "recent_24h": len(self.episodic.get_recent(24)),
            },
            "semantic": {
                "count": len(self.semantic.items),
                "high_confidence": len(self.semantic.get_high_confidence()),
            },
            "last_compression": self.last_compression.isoformat(),
        }


# Convenience function
def create_memory_system(base_path: Optional[str] = None) -> MultiTierMemory:
    """Create a multi-tier memory system"""
    return MultiTierMemory(base_path)
