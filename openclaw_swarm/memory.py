"""
Memory System - Persistent Memory for Agents
Inspired by: emipanelliok/engram, rcortx/kiwiq
"""

import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import hashlib
from rich.console import Console

console = Console()


@dataclass
class MemoryEntry:
    """A single memory entry"""

    id: str
    timestamp: str
    agent: str
    task: str
    input_data: str
    output_data: str
    success: bool
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Memory:
    """
    Persistent Memory System for Agents

    Features:
    - Store and retrieve agent experiences
    - Learn from past interactions
    - Search through memory by task, agent, or content
    - Compress old memories
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(
            storage_path
            or os.path.join(os.path.dirname(__file__), "..", "..", "data", "memory")
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.memories_file = self.storage_path / "memories.json"
        self.index_file = self.storage_path / "index.json"

        self.memories: Dict[str, MemoryEntry] = {}
        self.index: Dict[str, List[str]] = {
            "by_agent": {},
            "by_task": {},
            "by_success": {"true": [], "false": []},
        }

        self._load()

    def _load(self) -> None:
        """Load memories from disk"""
        if self.memories_file.exists():
            try:
                with open(self.memories_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.memories = {k: MemoryEntry(**v) for k, v in data.items()}
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load memories: {e}[/yellow]")

        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self.index = json.load(f)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load index: {e}[/yellow]")

    def _save(self) -> None:
        """Save memories to disk"""
        with open(self.memories_file, "w", encoding="utf-8") as f:
            json.dump(
                {k: asdict(v) for k, v in self.memories.items()},
                f,
                indent=2,
                ensure_ascii=False,
            )

        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    def _generate_id(self, agent: str, task: str, input_data: str) -> str:
        """Generate unique ID for memory entry"""
        content = f"{agent}:{task}:{input_data}:{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def store(
        self,
        agent: str,
        task: str,
        input_data: str,
        output_data: str,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a new memory entry

        Args:
            agent: Agent name
            task: Task type
            input_data: Input provided
            output_data: Output produced
            success: Whether the task succeeded
            metadata: Additional metadata

        Returns:
            Memory entry ID
        """
        entry_id = self._generate_id(agent, task, input_data)

        entry = MemoryEntry(
            id=entry_id,
            timestamp=datetime.now().isoformat(),
            agent=agent,
            task=task,
            input_data=input_data,
            output_data=output_data,
            success=success,
            metadata=metadata or {},
        )

        self.memories[entry_id] = entry

        # Update index
        if agent not in self.index["by_agent"]:
            self.index["by_agent"][agent] = []
        self.index["by_agent"][agent].append(entry_id)

        if task not in self.index["by_task"]:
            self.index["by_task"][task] = []
        self.index["by_task"][task].append(entry_id)

        success_key = "true" if success else "false"
        self.index["by_success"][success_key].append(entry_id)

        self._save()

        console.print(f"[green]Memory stored: {entry_id}[/green]")
        return entry_id

    def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a specific memory by ID"""
        return self.memories.get(entry_id)

    def search_by_agent(self, agent: str, limit: int = 10) -> List[MemoryEntry]:
        """Search memories by agent"""
        entry_ids = self.index["by_agent"].get(agent, [])[-limit:]
        return [self.memories[eid] for eid in entry_ids if eid in self.memories]

    def search_by_task(self, task: str, limit: int = 10) -> List[MemoryEntry]:
        """Search memories by task type"""
        entry_ids = self.index["by_task"].get(task, [])[-limit:]
        return [self.memories[eid] for eid in entry_ids if eid in self.memories]

    def search_successful(self, limit: int = 10) -> List[MemoryEntry]:
        """Get successful memories"""
        entry_ids = self.index["by_success"]["true"][-limit:]
        return [self.memories[eid] for eid in entry_ids if eid in self.memories]

    def search_failed(self, limit: int = 10) -> List[MemoryEntry]:
        """Get failed memories"""
        entry_ids = self.index["by_success"]["false"][-limit:]
        return [self.memories[eid] for eid in entry_ids if eid in self.memories]

    def find_similar(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        """
        Find similar memories by text matching

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching memories
        """
        query_lower = query.lower()
        results = []

        for entry in self.memories.values():
            if (
                query_lower in entry.input_data.lower()
                or query_lower in entry.output_data.lower()
                or query_lower in entry.task.lower()
            ):
                results.append(entry)

        # Sort by timestamp (most recent first)
        results.sort(key=lambda x: x.timestamp, reverse=True)

        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        total = len(self.memories)
        successful = len(self.index["by_success"]["true"])
        failed = len(self.index["by_success"]["false"])

        agents = list(self.index["by_agent"].keys())
        tasks = list(self.index["by_task"].keys())

        return {
            "total_memories": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "agents": len(agents),
            "tasks": len(tasks),
            "agent_distribution": {a: len(self.index["by_agent"][a]) for a in agents},
            "task_distribution": {t: len(self.index["by_task"][t]) for t in tasks},
        }

    def clear_old(self, days: int = 30) -> int:
        """Clear memories older than X days"""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

        to_remove = []
        for entry_id, entry in self.memories.items():
            entry_time = datetime.fromisoformat(entry.timestamp).timestamp()
            if entry_time < cutoff:
                to_remove.append(entry_id)

        for entry_id in to_remove:
            self._remove_entry(entry_id)

        self._save()

        console.print(f"[yellow]Cleared {len(to_remove)} old memories[/yellow]")
        return len(to_remove)

    def _remove_entry(self, entry_id: str) -> None:
        """Remove a memory entry from all indexes"""
        entry = self.memories.pop(entry_id, None)
        if not entry:
            return

        # Remove from indexes
        if entry.agent in self.index["by_agent"]:
            self.index["by_agent"][entry.agent] = [
                x for x in self.index["by_agent"][entry.agent] if x != entry_id
            ]

        if entry.task in self.index["by_task"]:
            self.index["by_task"][entry.task] = [
                x for x in self.index["by_task"][entry.task] if x != entry_id
            ]

        success_key = "true" if entry.success else "false"
        self.index["by_success"][success_key] = [
            x for x in self.index["by_success"][success_key] if x != entry_id
        ]

    def export(self, filepath: str) -> None:
        """Export memories to file"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                {k: asdict(v) for k, v in self.memories.items()},
                f,
                indent=2,
                ensure_ascii=False,
            )
        console.print(
            f"[green]Exported {len(self.memories)} memories to {filepath}[/green]"
        )

    def import_memories(self, filepath: str) -> int:
        """Import memories from file"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for entry_id, entry_data in data.items():
            if entry_id not in self.memories:
                entry = MemoryEntry(**entry_data)
                self.memories[entry_id] = entry
                self._add_to_index(entry)
                count += 1

        self._save()
        console.print(f"[green]Imported {count} new memories[/green]")
        return count

    def _add_to_index(self, entry: MemoryEntry) -> None:
        """Add entry to all indexes"""
        if entry.agent not in self.index["by_agent"]:
            self.index["by_agent"][entry.agent] = []
        self.index["by_agent"][entry.agent].append(entry.id)

        if entry.task not in self.index["by_task"]:
            self.index["by_task"][entry.task] = []
        self.index["by_task"][entry.task].append(entry.id)

        success_key = "true" if entry.success else "false"
        self.index["by_success"][success_key].append(entry.id)


# Convenience functions
def remember(
    agent: str,
    task: str,
    input_data: str,
    output_data: str,
    success: bool,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Quick store memory"""
    memory = Memory()
    return memory.store(agent, task, input_data, output_data, success, metadata)


def recall(query: str, limit: int = 5) -> List[MemoryEntry]:
    """Quick search memories"""
    memory = Memory()
    return memory.find_similar(query, limit)
