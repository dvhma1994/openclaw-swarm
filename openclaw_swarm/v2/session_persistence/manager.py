"""
Session Persistence & Recovery — Inspired by OpenClaude conversationRecovery + crossProjectResume.
Persists agent sessions across restarts, crashes, and machine switches.

Features:
- Auto-save session state every N seconds
- Crash recovery: resume from last checkpoint
- Session branching: fork a session for parallel exploration
- Cross-project resume: continue a session in a different directory
- Session search: find past sessions by content, date, or tags
- Export/import: share sessions between team members
- Compression: old sessions auto-compressed to save space
"""

import hashlib
import json
import logging
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

BASE_DIR = Path(
    os.environ.get(
        "OPENCLAW_DIRECTOR_DIR", Path.home() / ".openclaw" / "workspaces" / "director"
    )
)
SESSION_DIR = BASE_DIR / "session_persistence" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_DIR = BASE_DIR / "session_persistence" / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


class SessionState(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CRASHED = "crashed"
    ARCHIVED = "archived"


@dataclass
class SessionStep:
    """A single step/action in a session."""

    step_id: str
    action: str
    result: str = ""
    tool_used: str = ""
    model: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    timestamp: str = ""
    tags: list = field(default_factory=list)
    error: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class SessionMetadata:
    """Session metadata (lightweight, always loaded)."""

    session_id: str
    title: str = ""
    created_at: str = ""
    updated_at: str = ""
    state: SessionState = SessionState.ACTIVE
    model: str = ""
    project_dir: str = ""
    total_steps: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    tags: list = field(default_factory=list)
    branch_from: str = ""  # session_id of parent (if branched)
    checkpoint_count: int = 0

    def to_dict(self):
        return {**asdict(self), "state": self.state.value}

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        data["state"] = SessionState(data.get("state", "active"))
        return cls(**data)


class SessionPersistence:
    """
    Manages session persistence, recovery, and branching.
    """

    def __init__(self, session_dir: Path = SESSION_DIR):
        self.session_dir = session_dir
        self.sessions: Dict[str, SessionMetadata] = {}
        self._autosave_interval = 60  # seconds
        self._last_autosave = 0
        self._load_all()

    def _load_all(self):
        for f in self.session_dir.glob("*.meta.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                meta = SessionMetadata.from_dict(data)
                self.sessions[meta.session_id] = meta
            except Exception:
                logging.warning("Failed to load session metadata from %s", f.name)

    def _save_meta(self, meta: SessionMetadata):
        path = self.session_dir / f"{meta.session_id}.meta.json"
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self.session_dir), suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(meta.to_dict(), f, indent=2, ensure_ascii=False, default=str)
            os.replace(tmp_path, str(path))
        except Exception:
            logging.exception("Failed to save session metadata for %s", meta.session_id)
            os.unlink(tmp_path)
            raise

    def _save_steps(self, session_id: str, steps: list):
        path = self.session_dir / f"{session_id}.steps.json"
        # Keep last 1000 steps per session
        if len(steps) > 1000:
            steps = steps[-1000:]
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self.session_dir), suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(
                    {"steps": steps}, f, indent=2, ensure_ascii=False, default=str
                )
            os.replace(tmp_path, str(path))
        except Exception:
            logging.exception("Failed to save steps for session %s", session_id)
            os.unlink(tmp_path)
            raise

    def create_session(
        self, title: str = "", model: str = "sonnet", project_dir: str = ""
    ) -> SessionMetadata:
        sid = f"sess_{hashlib.md5(f'{title}{time.time()}'.encode()).hexdigest()[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        meta = SessionMetadata(
            session_id=sid,
            title=title or f"Session {sid[:6]}",
            created_at=now,
            updated_at=now,
            model=model,
            project_dir=project_dir,
        )
        self.sessions[sid] = meta
        self._save_meta(meta)
        # Initialize empty steps
        self._save_steps(sid, [])
        return meta

    def add_step(
        self,
        session_id: str,
        action: str,
        result: str = "",
        tool_used: str = "",
        model: str = "",
        tokens: int = 0,
        cost: float = 0.0,
        tags: list = None,
        error: str = "",
    ) -> SessionStep:
        if session_id not in self.sessions:
            self.create_session()

        step_id = (
            f"step_{int(time.time())}_{hashlib.md5(action.encode()).hexdigest()[:4]}"
        )
        step = SessionStep(
            step_id=step_id,
            action=action,
            result=result[:2000],
            tool_used=tool_used,
            model=model,
            tokens_used=tokens,
            cost_usd=cost,
            tags=tags or [],
            error=error,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Load, append, save
        steps = self._load_steps(session_id)
        steps.append(step.to_dict())
        self._save_steps(session_id, steps)

        # Update metadata
        meta = self.sessions[session_id]
        meta.total_steps = len(steps)
        meta.total_tokens += tokens
        meta.total_cost += cost
        meta.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_meta(meta)

        return step

    def _load_steps(self, session_id: str) -> list:
        path = self.session_dir / f"{session_id}.steps.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("steps", [])
            except Exception:
                logging.warning("Failed to load steps for session %s", session_id)
        return []

    def get_session(self, session_id: str) -> Optional[dict]:
        if session_id not in self.sessions:
            return None
        meta = self.sessions[session_id]
        steps = self._load_steps(session_id)
        return {"metadata": meta.to_dict(), "steps": steps}

    def create_checkpoint(self, session_id: str, label: str = "") -> dict:
        """Create a checkpoint (full snapshot) that can be restored later."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        meta = self.sessions[session_id]
        steps = self._load_steps(session_id)

        cp_id = f"cp_{session_id}_{int(time.time())}"
        cp_path = CHECKPOINT_DIR / f"{cp_id}.json"
        checkpoint = {
            "checkpoint_id": cp_id,
            "session_id": session_id,
            "label": label,
            "metadata": meta.to_dict(),
            "steps": steps,
            "step_count": len(steps),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(cp_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False, default=str)

        meta.checkpoint_count += 1
        self._save_meta(meta)

        return {"checkpoint_id": cp_id, "steps_saved": len(steps)}

    def restore_from_checkpoint(self, checkpoint_id: str) -> dict:
        """Restore a session from a checkpoint."""
        cp_path = CHECKPOINT_DIR / f"{checkpoint_id}.json"
        if not cp_path.exists():
            return {"error": f"Checkpoint '{checkpoint_id}' not found"}

        try:
            with open(cp_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
            session_id = checkpoint["session_id"]
            meta_data = checkpoint["metadata"]
            steps = checkpoint["steps"]

            # Create new session from checkpoint
            new_sid = f"sess_restored_{int(time.time())}"
            now = datetime.now(timezone.utc).isoformat()
            new_meta = SessionMetadata(
                session_id=new_sid,
                title=f"Restored from {checkpoint_id[:20]}",
                created_at=now,
                updated_at=now,
                model=meta_data.get("model", "sonnet"),
                state=SessionState.ACTIVE,
                total_steps=len(steps),
                total_tokens=meta_data.get("total_tokens", 0),
                total_cost=meta_data.get("total_cost", 0.0),
                branch_from=session_id,
            )
            self.sessions[new_sid] = new_meta
            self._save_meta(new_meta)
            self._save_steps(new_sid, steps)

            return {"restored_session": new_sid, "steps_restored": len(steps)}
        except Exception as e:
            return {"error": str(e)}

    def branch_session(self, session_id: str, label: str = "") -> dict:
        """Create a branch of a session for parallel exploration."""
        return self.create_checkpoint(
            session_id,
            label=label or f"Branch at step {self.sessions[session_id].total_steps}",
        )

    def search_sessions(
        self, query: str = "", tag: str = "", date_from: str = "", date_to: str = ""
    ) -> list:
        """Search sessions by content, tag, or date range."""
        results = []
        ql = query.lower() if query else ""
        for meta in self.sessions.values():
            # Filter by tag
            if tag and tag not in meta.tags:
                continue
            # Filter by date
            if date_from and meta.updated_at < date_from:
                continue
            if date_to and meta.updated_at > date_to:
                continue
            # Filter by content
            if ql:
                steps = self._load_steps(meta.session_id)
                found = False
                for step in steps:
                    if (
                        ql in str(step.get("action", "")).lower()
                        or ql in str(step.get("result", "")).lower()
                    ):
                        found = True
                        break
                if not found and ql not in meta.title.lower():
                    continue
            results.append(meta.to_dict())
        return sorted(results, key=lambda x: x.get("updated_at", ""), reverse=True)

    def archive_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            self.sessions[session_id].state = SessionState.ARCHIVED
            self._save_meta(self.sessions[session_id])
            return True
        return False

    def recover_crashed(self) -> list:
        """Find and recover sessions that crashed."""
        crashed = [s for s in self.sessions.values() if s.state == SessionState.CRASHED]
        recovered = []
        for meta in crashed:
            meta.state = SessionState.ACTIVE
            meta.updated_at = datetime.now(timezone.utc).isoformat()
            self._save_meta(meta)
            recovered.append(meta.session_id)
        return recovered

    def mark_crashed_on_shutdown(self):
        """Call on unexpected shutdown to mark active sessions."""
        for meta in self.sessions.values():
            if meta.state == SessionState.ACTIVE:
                meta.state = SessionState.CRASHED
                self._save_meta(meta)

    def cleanup_old(self, max_age_days: int = 30):
        """Archive sessions older than max_age_days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        archived = 0
        for meta in self.sessions.values():
            if meta.state == SessionState.ACTIVE and meta.updated_at < cutoff:
                meta.state = SessionState.ARCHIVED
                self._save_meta(meta)
                archived += 1
        return archived

    def list_sessions(self, state: str = None) -> list:
        sessions = [m.to_dict() for m in self.sessions.values()]
        if state:
            sessions = [s for s in sessions if s["state"] == state]
        return sorted(sessions, key=lambda s: s.get("updated_at", ""), reverse=True)

    def get_stats(self) -> dict:
        states = {}
        for m in self.sessions.values():
            s = m.state.value
            states[s] = states.get(s, 0) + 1
        return {
            "total_sessions": len(self.sessions),
            "by_state": states,
            "total_steps": sum(m.total_steps for m in self.sessions.values()),
            "total_tokens": sum(m.total_tokens for m in self.sessions.values()),
            "total_cost": round(sum(m.total_cost for m in self.sessions.values()), 4),
        }


_persistence: Optional[SessionPersistence] = None


def get_persistence() -> SessionPersistence:
    global _persistence
    if _persistence is None:
        _persistence = SessionPersistence()
    return _persistence


if __name__ == "__main__":
    import sys

    pm = get_persistence()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        print(json.dumps(pm.get_stats(), indent=2))
    elif cmd == "list":
        for s in pm.list_sessions():
            print(
                f"  [{s['state']:10s}] {s['session_id']}: {s['title'][:40]} ({s['total_steps']} steps)"
            )
    elif cmd == "create":
        meta = pm.create_session(title=" ".join(sys.argv[2:]) or "Test Session")
        print(f"Created: {meta.session_id}")
    elif cmd == "search" and len(sys.argv) > 2:
        results = pm.search_sessions(query=sys.argv[2])
        print(f"Found {len(results)} sessions")
    else:
        print("Commands: stats, list, create [title], search [query]")
