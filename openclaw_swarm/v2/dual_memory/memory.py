"""
Dual-Layer Memory System - Inspired by Skynet Agent.
Layer 1: Automatic Memory (RAG) - Background vectors for fast recall
Layer 2: Conscious Memory - Deliberate, tagged, importance-scored
Layer 3: Knowledge Graph - Entity-relationship mapping
"""

import hashlib
import json
import logging
import math
import os
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(
    os.environ.get(
        "OPENCLAW_DIRECTOR_DIR", Path.home() / ".openclaw" / "workspaces" / "director"
    )
)
MEMORY_DIR = BASE_DIR / "dual_memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
AUTO_FILE = MEMORY_DIR / "automatic_memory.json"
CONSCIOUS_FILE = MEMORY_DIR / "conscious_memory.json"
KG_FILE = MEMORY_DIR / "knowledge_graph.json"


@dataclass
class AutoMemoryEntry:
    entry_id: str
    text: str
    source: str = "conversation"
    sender: str = ""
    timestamp: str = ""
    session_id: str = ""
    tags: list = field(default_factory=list)
    embedding_hash: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class ConsciousMemoryEntry:
    entry_id: str
    content: str
    tags: list = field(default_factory=list)
    importance: int = 5
    source: str = "explicit"
    access_count: int = 0
    last_accessed: str = ""
    created_at: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

    def touch(self):
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc).isoformat()


@dataclass
class KnowledgeNode:
    node_id: str
    entity: str
    entity_type: str = "concept"
    properties: dict = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class KnowledgeEdge:
    edge_id: str
    source_id: str
    target_id: str
    relation: str = "related_to"
    weight: float = 1.0
    evidence: str = ""
    created_at: str = ""

    def to_dict(self):
        return asdict(self)


class AutomaticMemory:
    """Layer 1: Background RAG memory with TF-IDF-like retrieval."""

    def __init__(self, store_path: Path = AUTO_FILE):
        self.store_path = store_path
        self.entries: Dict[str, AutoMemoryEntry] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if self.store_path.exists():
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for e in data.get("entries", []):
                    entry = AutoMemoryEntry(**e)
                    self.entries[entry.entry_id] = entry
            except Exception:
                logging.exception("Failed to load automatic memory")

    def _save(self):
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(self.store_path.parent), suffix=".tmp"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "entries": [e.to_dict() for e in self.entries.values()],
                        "count": len(self.entries),
                        "updated": datetime.now(timezone.utc).isoformat(),
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            os.replace(tmp_path, str(self.store_path))
        except Exception:
            logging.exception("Failed to save automatic memory")
            os.unlink(tmp_path)
            raise

    def store(
        self,
        text: str,
        source: str = "conversation",
        sender: str = "",
        session_id: str = "",
        tags: list = None,
    ) -> str:
        eid = f"auto_{hashlib.md5(text[:200].encode()).hexdigest()[:8]}_{int(time.time())}"
        entry = AutoMemoryEntry(
            entry_id=eid,
            text=text,
            source=source,
            sender=sender,
            session_id=session_id,
            tags=tags or [],
            timestamp=datetime.now(timezone.utc).isoformat(),
            embedding_hash=hashlib.sha256(text.encode()).hexdigest()[:16],
        )
        with self._lock:
            self.entries[eid] = entry
            self._save()
        return eid

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        query_terms = set(query.lower().split())
        scored = []
        for entry in self.entries.values():
            entry_terms = set(entry.text.lower().split())
            overlap = len(query_terms & entry_terms)
            if overlap > 0:
                score = overlap / math.log(len(entry_terms) + 2)
                scored.append({"entry": entry.to_dict(), "score": round(score, 3)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def consolidate_candidates(self, min_age_hours: int = 24) -> List[AutoMemoryEntry]:
        cutoff = datetime.now(timezone.utc).timestamp() - min_age_hours * 3600
        seen = {}
        for entry in self.entries.values():
            ts = (
                datetime.fromisoformat(entry.timestamp).timestamp()
                if entry.timestamp
                else 0
            )
            if ts < cutoff:
                seen.setdefault(entry.embedding_hash, []).append(entry)
        candidates = []
        for h, entries in seen.items():
            if len(entries) >= 2:
                candidates.extend(entries)
        return candidates

    def get_stats(self):
        return {
            "total_entries": len(self.entries),
            "sources": list(set(e.source for e in self.entries.values())),
        }


class ConsciousMemory:
    """Layer 2: Deliberate, tagged, importance-scored memory."""

    def __init__(self, store_path: Path = CONSCIOUS_FILE):
        self.store_path = store_path
        self.entries: Dict[str, ConsciousMemoryEntry] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if self.store_path.exists():
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for e in data.get("entries", []):
                    self.entries[e["entry_id"]] = ConsciousMemoryEntry(**e)
            except Exception:
                logging.exception("Failed to load conscious memory")

    def _save(self):
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(self.store_path.parent), suffix=".tmp"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "entries": [e.to_dict() for e in self.entries.values()],
                        "count": len(self.entries),
                        "updated": datetime.now(timezone.utc).isoformat(),
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            os.replace(tmp_path, str(self.store_path))
        except Exception:
            logging.exception("Failed to save conscious memory")
            os.unlink(tmp_path)
            raise

    def save(
        self,
        content: str,
        tags: list = None,
        importance: int = 5,
        source: str = "explicit",
        metadata: dict = None,
    ) -> str:
        eid = f"cons_{hashlib.md5(content[:200].encode()).hexdigest()[:8]}_{int(time.time())}"
        entry = ConsciousMemoryEntry(
            entry_id=eid,
            content=content,
            tags=tags or [],
            importance=max(1, min(10, importance)),
            source=source,
            created_at=datetime.now(timezone.utc).isoformat(),
            last_accessed=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        with self._lock:
            self.entries[eid] = entry
            self._save()
        return eid

    def search(
        self,
        query: str = "",
        tags: list = None,
        min_importance: int = 1,
        top_k: int = 10,
    ) -> List[dict]:
        results = []
        query_terms = set(query.lower().split()) if query else set()
        for entry in self.entries.values():
            if entry.importance < min_importance:
                continue
            if tags and not any(t in entry.tags for t in tags):
                continue
            if query_terms:
                entry_terms = set(entry.content.lower().split())
                overlap = len(query_terms & entry_terms)
                if overlap == 0 and not tags:
                    continue
                score = overlap / math.log(len(entry_terms) + 2) if entry_terms else 0
            else:
                score = entry.importance / 10.0
            entry.touch()
            results.append({"entry": entry.to_dict(), "score": round(score, 3)})
        results.sort(key=lambda x: x["score"], reverse=True)
        self._save()
        return results[:top_k]

    def update(
        self,
        entry_id: str,
        content: str = None,
        tags: list = None,
        importance: int = None,
    ) -> bool:
        if entry_id not in self.entries:
            return False
        e = self.entries[entry_id]
        if content is not None:
            e.content = content
        if tags is not None:
            e.tags = tags
        if importance is not None:
            e.importance = max(1, min(10, importance))
        e.last_accessed = datetime.now(timezone.utc).isoformat()
        self._save()
        return True

    def delete(self, entry_id: str) -> bool:
        if entry_id in self.entries:
            del self.entries[entry_id]
            self._save()
            return True
        return False

    def get_important(self, min_importance: int = 7) -> List[ConsciousMemoryEntry]:
        return [e for e in self.entries.values() if e.importance >= min_importance]

    def consolidate_from_automatic(self, auto_mem: AutomaticMemory) -> int:
        candidates = auto_mem.consolidate_candidates(min_age_hours=12)
        promoted = 0
        for entry in candidates:
            existing = self.search(query=entry.text[:100], top_k=3)
            if existing and existing[0]["score"] > 0.5:
                continue
            self.save(
                content=entry.text[:2000],
                tags=entry.tags + [entry.source, "auto_consolidated"],
                importance=6,
                source="consolidated",
                metadata={"auto_entry_id": entry.entry_id},
            )
            promoted += 1
        return promoted

    def get_stats(self):
        return {
            "total_entries": len(self.entries),
            "avg_importance": round(
                sum(e.importance for e in self.entries.values())
                / max(len(self.entries), 1),
                1,
            ),
            "by_source": {
                s: sum(1 for e in self.entries.values() if e.source == s)
                for s in set(e.source for e in self.entries.values())
            },
        }


class KnowledgeGraph:
    """Layer 3: Entity-relationship knowledge graph."""

    def __init__(self, store_path: Path = KG_FILE):
        self.store_path = store_path
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: Dict[str, KnowledgeEdge] = {}
        self._load()

    def _load(self):
        if self.store_path.exists():
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for n in data.get("nodes", []):
                    self.nodes[n["node_id"]] = KnowledgeNode(**n)
                for e in data.get("edges", []):
                    self.edges[e["edge_id"]] = KnowledgeEdge(**e)
            except Exception:
                logging.exception("Failed to load knowledge graph")

    def _save(self):
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(self.store_path.parent), suffix=".tmp"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "nodes": [n.to_dict() for n in self.nodes.values()],
                        "edges": [e.to_dict() for e in self.edges.values()],
                        "updated": datetime.now(timezone.utc).isoformat(),
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            os.replace(tmp_path, str(self.store_path))
        except Exception:
            logging.exception("Failed to save knowledge graph")
            os.unlink(tmp_path)
            raise

    def add_node(
        self, entity: str, entity_type: str = "concept", properties: dict = None
    ) -> str:
        nid = f"n_{hashlib.md5(entity.encode()).hexdigest()[:8]}"
        if nid not in self.nodes:
            self.nodes[nid] = KnowledgeNode(
                node_id=nid,
                entity=entity,
                entity_type=entity_type,
                properties=properties or {},
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._save()
        return nid

    def add_edge(
        self,
        source_entity: str,
        target_entity: str,
        relation: str = "related_to",
        weight: float = 1.0,
        evidence: str = "",
    ) -> str:
        src_id = self.add_node(source_entity)
        tgt_id = self.add_node(target_entity)
        eid = (
            f"e_{hashlib.md5(f'{src_id}-{relation}-{tgt_id}'.encode()).hexdigest()[:8]}"
        )
        if eid not in self.edges:
            self.edges[eid] = KnowledgeEdge(
                edge_id=eid,
                source_id=src_id,
                target_id=tgt_id,
                relation=relation,
                weight=weight,
                evidence=evidence,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._save()
        else:
            self.edges[eid].weight = max(self.edges[eid].weight, weight)
            self._save()
        return eid

    def get_neighbors(self, entity: str) -> List[dict]:
        nid = f"n_{hashlib.md5(entity.encode()).hexdigest()[:8]}"
        neighbors = []
        for edge in self.edges.values():
            if edge.source_id == nid:
                t = self.nodes.get(edge.target_id)
                if t:
                    neighbors.append(
                        {
                            "entity": t.entity,
                            "relation": edge.relation,
                            "weight": edge.weight,
                        }
                    )
            elif edge.target_id == nid:
                s = self.nodes.get(edge.source_id)
                if s:
                    neighbors.append(
                        {
                            "entity": s.entity,
                            "relation": f"inverse_{edge.relation}",
                            "weight": edge.weight,
                        }
                    )
        return sorted(neighbors, key=lambda x: x["weight"], reverse=True)

    def find_path(
        self, from_entity: str, to_entity: str, max_depth: int = 5
    ) -> List[str]:
        fid = self.add_node(from_entity)
        tid = self.add_node(to_entity)
        if fid == tid:
            return [from_entity]
        visited = {fid}
        queue = [(fid, [from_entity])]
        depth = 0
        while queue and depth < max_depth:
            cid, path = queue.pop(0)
            for edge in self.edges.values():
                nid = None
                nentity = None
                if edge.source_id == cid and edge.target_id not in visited:
                    nid = edge.target_id
                    t = self.nodes.get(nid)
                    nentity = t.entity if t else "?"
                elif edge.target_id == cid and edge.source_id not in visited:
                    nid = edge.source_id
                    s = self.nodes.get(nid)
                    nentity = s.entity if s else "?"
                if nid and nid not in visited:
                    p = path + [f"{edge.relation} -> {nentity}"]
                    if nid == tid:
                        return p
                    visited.add(nid)
                    queue.append((nid, p))
            depth += 1
        return []

    def get_stats(self):
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "relations": list(set(e.relation for e in self.edges.values())),
            "entity_types": list(set(n.entity_type for n in self.nodes.values())),
        }


class DualMemorySystem:
    """Unified interface: store, recall, consolidate across all layers."""

    def __init__(self):
        self.auto = AutomaticMemory()
        self.conscious = ConsciousMemory()
        self.kg = KnowledgeGraph()

    def remember(
        self,
        content: str,
        tags: list = None,
        importance: int = 5,
        source: str = "explicit",
    ) -> dict:
        auto_id = self.auto.store(content, source=source, tags=tags)
        cons_id = self.conscious.save(
            content, tags=tags, importance=importance, source=source
        )
        return {"auto_id": auto_id, "conscious_id": cons_id}

    def recall(self, query: str, top_k: int = 5) -> dict:
        return {
            "automatic": self.auto.search(query, top_k=top_k),
            "conscious": self.conscious.search(query=query, top_k=top_k),
            "knowledge_graph": (
                self.kg.get_neighbors(query) if len(query.split()) <= 3 else []
            ),
        }

    def consolidate(self) -> dict:
        promoted = self.conscious.consolidate_from_automatic(self.auto)
        return {
            "promoted": promoted,
            "auto_total": len(self.auto.entries),
            "conscious_total": len(self.conscious.entries),
        }

    def learn_relationship(
        self, e1: str, e2: str, relation: str = "related_to", evidence: str = ""
    ) -> str:
        return self.kg.add_edge(e1, e2, relation, evidence=evidence)

    def get_stats(self) -> dict:
        return {
            "automatic": self.auto.get_stats(),
            "conscious": self.conscious.get_stats(),
            "knowledge_graph": self.kg.get_stats(),
        }


_memory: Optional[DualMemorySystem] = None


def get_dual_memory() -> DualMemorySystem:
    global _memory
    if _memory is None:
        _memory = DualMemorySystem()
    return _memory


if __name__ == "__main__":
    import sys

    mem = get_dual_memory()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        print(json.dumps(mem.get_stats(), indent=2))
    elif cmd == "remember" and len(sys.argv) > 2:
        ids = mem.remember(
            sys.argv[2], importance=int(sys.argv[3]) if len(sys.argv) > 3 else 5
        )
        print(f"Stored: {ids}")
    elif cmd == "recall" and len(sys.argv) > 2:
        print(json.dumps(mem.recall(sys.argv[2]), indent=2, default=str))
    elif cmd == "consolidate":
        print(json.dumps(mem.consolidate(), indent=2))
    elif cmd == "learn" and len(sys.argv) > 4:
        mem.learn_relationship(sys.argv[2], sys.argv[3], sys.argv[4])
        print(f"Learned: {sys.argv[2]} -{sys.argv[4]}-> {sys.argv[3]}")
    else:
        print(
            "Commands: stats, remember <text> [imp], recall <query>, consolidate, learn <e1> <e2> <rel>"
        )
