"""
Web UI Server — Inspired by Blade Code (web mode) + Kilocode (VS Code extension).
Provides a browser-based interface alongside the CLI.

Features:
- Real-time chat interface with streaming responses
- Live context window meter
- Tool execution viewer (read/edit/search/bash logs)
- Agent status panel
- Memory browser (automatic + conscious + KG)
- Credential pool health dashboard
- Skills marketplace browser
- Session history with search
- File viewer/editor
- REST API for programmatic access

Tech: Pure Python HTTP server (no external deps) + WebSocket for live updates
"""

import hashlib
import json
import os
import threading
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

BASE_DIR = Path(
    os.environ.get(
        "OPENCLAW_DIRECTOR_DIR", Path.home() / ".openclaw" / "workspaces" / "director"
    )
)
WEB_DIR = BASE_DIR / "web_ui"
WEB_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR = WEB_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class WebMessage:
    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: str = ""
    tool_name: str = ""
    tool_result: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class WebSession:
    session_id: str
    messages: list = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    model: str = ""
    total_tokens: int = 0
    total_cost: float = 0.0

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "model": self.model,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
        }


class SessionManager:
    """Manages web UI sessions with persistence."""

    def __init__(self, sessions_dir: Path = SESSIONS_DIR):
        self.sessions_dir = sessions_dir
        self.sessions: Dict[str, WebSession] = {}
        self._load_all()

    def _load_all(self):
        for f in self.sessions_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                sid = data["session_id"]
                session = WebSession(
                    session_id=sid,
                    messages=data.get("messages", []),
                    created_at=data.get("created_at", ""),
                    updated_at=data.get("updated_at", ""),
                    model=data.get("model", ""),
                    total_tokens=data.get("total_tokens", 0),
                    total_cost=data.get("total_cost", 0.0),
                )
                self.sessions[sid] = session
            except Exception:
                pass

    def create_session(self, model: str = "sonnet") -> WebSession:
        sid = f"sess_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        session = WebSession(
            session_id=sid,
            model=model,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self.sessions[sid] = session
        self._save(session)
        return session

    def get_session(self, session_id: str) -> Optional[WebSession]:
        return self.sessions.get(session_id)

    def add_message(self, session_id: str, msg: WebMessage):
        if session_id not in self.sessions:
            self.create_session()
        session = self.sessions[session_id]
        msg.timestamp = datetime.now(timezone.utc).isoformat()
        session.messages.append(msg.to_dict())
        session.updated_at = datetime.now(timezone.utc).isoformat()
        self._save(session)

    def list_sessions(self) -> list:
        return [
            s.to_dict()
            for s in sorted(
                self.sessions.values(), key=lambda s: s.updated_at or "", reverse=True
            )
        ]

    def search_sessions(self, query: str) -> list:
        results = []
        ql = query.lower()
        for session in self.sessions.values():
            for msg in session.messages:
                if ql in str(msg.get("content", "")).lower():
                    results.append(session.to_dict())
                    break
        return results

    def _save(self, session: WebSession):
        path = self.sessions_dir / f"{session.session_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "session_id": session.session_id,
                    "messages": session.messages[-100:],  # Keep last 100
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "model": session.model,
                    "total_tokens": session.total_tokens,
                    "total_cost": session.total_cost,
                },
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            path = self.sessions_dir / f"{session_id}.json"
            if path.exists():
                path.unlink()
            return True
        return False


class WebUIAPI:
    """
    REST API for the web interface.
    Endpoints:
      GET  /api/status          — System status (all v2 systems)
      GET  /api/sessions        — List sessions
      POST /api/sessions        — Create session
      GET  /api/sessions/:id    — Get session with messages
      POST /api/sessions/:id/msg — Send message to session
      DELETE /api/sessions/:id  — Delete session
      GET  /api/memory          — Memory system status
      POST /api/memory/recall   — Search memory
      GET  /api/skills           — List available skills
      POST /api/skills/install   — Install a skill
      GET  /api/credentials      — Credential pool health
      GET  /api/evolution         — Evolution engine stats
      GET  /api/swarm            — Swarm orchestrator stats
      GET  /api/guardian         — Constitutional guardian status
    """

    def __init__(self):
        self.session_mgr = SessionManager()

    def handle_request(self, method: str, path: str, body: dict = None) -> dict:
        try:
            parts = path.strip("/").split("/")
            if not parts or parts[0] == "":
                return self._serve_home()

            # /api/ prefix
            if parts[0] == "api":
                return self._handle_api(method, parts[1:], body or {})
            return {"error": "Not found", "path": path}
        except Exception as e:
            return {"error": str(e), "traceback": traceback.format_exc()[:200]}

    def _handle_api(self, method: str, parts: list, body: dict) -> dict:
        if not parts:
            return {
                "endpoints": [
                    "status",
                    "sessions",
                    "memory",
                    "skills",
                    "credentials",
                    "evolution",
                    "swarm",
                    "guardian",
                    "hud",
                ]
            }

        endpoint = parts[0]

        if endpoint == "status":
            return self._get_status()
        elif endpoint == "sessions":
            return self._handle_sessions(method, parts[1:], body)
        elif endpoint == "memory":
            return self._handle_memory(method, parts[1:], body)
        elif endpoint == "skills":
            return self._handle_skills(method, parts[1:], body)
        elif endpoint == "credentials":
            return self._handle_credentials()
        elif endpoint == "evolution":
            return self._handle_evolution()
        elif endpoint == "swarm":
            return self._handle_swarm()
        elif endpoint == "guardian":
            return self._handle_guardian()
        elif endpoint == "hud":
            return self._handle_hud()
        return {"error": f"Unknown endpoint: {endpoint}"}

    def _get_status(self) -> dict:
        status = {"timestamp": datetime.now(timezone.utc).isoformat(), "systems": {}}
        try:
            from evolution_engine.engine import get_evolution_engine

            status["systems"]["evolution"] = get_evolution_engine().get_stats()
        except Exception:
            pass
        try:
            from swarm_orchestrator.orchestrator import get_swarm

            status["systems"]["swarm"] = get_swarm().get_stats()
        except Exception:
            pass
        try:
            from dual_memory.memory import get_dual_memory

            status["systems"]["memory"] = get_dual_memory().get_stats()
        except Exception:
            pass
        try:
            from credential_pool.pool import get_credential_pool

            status["systems"]["credentials"] = get_credential_pool().get_stats()
        except Exception:
            pass
        try:
            from skills_marketplace.marketplace import get_marketplace

            status["systems"]["skills"] = get_marketplace().get_stats()
        except Exception:
            pass
        try:
            from constitutional_guardian_v2 import get_guardian

            status["systems"]["guardian"] = get_guardian().get_full_status()
        except Exception:
            pass
        return status

    def _handle_sessions(self, method: str, parts: list, body: dict) -> dict:
        if not parts:
            if method == "GET":
                return {"sessions": self.session_mgr.list_sessions()}
            elif method == "POST":
                session = self.session_mgr.create_session(body.get("model", "sonnet"))
                return {"session": session.to_dict()}
        elif len(parts) == 1:
            sid = parts[0]
            if method == "GET":
                session = self.session_mgr.get_session(sid)
                return {
                    "session": session.to_dict() if session else None,
                    "messages": session.messages if session else [],
                }
            elif method == "DELETE":
                return {"deleted": self.session_mgr.delete_session(sid)}
        elif len(parts) == 2 and parts[1] == "msg":
            sid = parts[0]
            if method == "POST":
                content = body.get("content", "")
                role = body.get("role", "user")
                msg = WebMessage(
                    role=role, content=content, tool_name=body.get("tool_name", "")
                )
                self.session_mgr.add_message(sid, msg)
                return {"added": True, "session_id": sid}
        return {"error": "Invalid session request"}

    def _handle_memory(self, method: str, parts: list, body: dict) -> dict:
        try:
            from dual_memory.memory import get_dual_memory

            mem = get_dual_memory()
            if not parts:
                return mem.get_stats()
            elif parts[0] == "recall" and method == "POST":
                query = body.get("query", "")
                return mem.recall(query)
            elif parts[0] == "remember" and method == "POST":
                ids = mem.remember(
                    content=body.get("content", ""),
                    tags=body.get("tags", []),
                    importance=body.get("importance", 5),
                )
                return {"stored": ids}
            elif parts[0] == "consolidate":
                return mem.consolidate()
            elif parts[0] == "learn" and method == "POST":
                eid = mem.learn_relationship(
                    body.get("entity1", ""),
                    body.get("entity2", ""),
                    body.get("relation", "related_to"),
                )
                return {"edge_id": eid}
        except Exception as e:
            return {"error": str(e)}
        return {"error": "Invalid memory request"}

    def _handle_skills(self, method: str, parts: list, body: dict) -> dict:
        try:
            from skills_marketplace.marketplace import get_marketplace

            mp = get_marketplace()
            if not parts:
                return mp.get_stats()
            elif parts[0] == "search":
                results = mp.search(
                    query=body.get("query", ""),
                    category=body.get("category", ""),
                    risk=body.get("risk", ""),
                )
                return {"skills": [s.to_dict() for s in results]}
            elif parts[0] == "install" and method == "POST":
                return mp.install(body.get("skill_id", ""))
        except Exception as e:
            return {"error": str(e)}
        return {"error": "Invalid skills request"}

    def _handle_credentials(self) -> dict:
        try:
            from credential_pool.pool import get_credential_pool

            return get_credential_pool().health_check()
        except Exception as e:
            return {"error": str(e)}

    def _handle_evolution(self) -> dict:
        try:
            from evolution_engine.engine import get_evolution_engine

            e = get_evolution_engine()
            stats = e.get_stats()
            stats["recurring_failures"] = [
                {
                    "pattern": f.pattern_id,
                    "occurrences": f.occurrences,
                    "desc": f.description,
                }
                for f in e.get_recurring_failures()[:5]
            ]
            return stats
        except Exception as e:
            return {"error": str(e)}

    def _handle_swarm(self) -> dict:
        try:
            from swarm_orchestrator.orchestrator import get_swarm

            return get_swarm().get_stats()
        except Exception as e:
            return {"error": str(e)}

    def _handle_guardian(self) -> dict:
        try:
            from constitutional_guardian_v2 import get_guardian

            return get_guardian().get_full_status()
        except Exception as e:
            return {"error": str(e)}

    def _handle_hud(self) -> dict:
        try:
            from realtime_hud.dashboard import get_hud

            hud = get_hud()
            hud.collect_from_systems()
            return hud.metrics.to_dict()
        except Exception as e:
            return {"error": str(e)}

    def _serve_home(self) -> dict:
        return {
            "name": "OpenClaw v2 Web UI",
            "version": "2.0.0",
            "api_endpoints": [
                "GET  /api/status",
                "GET  /api/sessions",
                "POST /api/sessions",
                "GET  /api/sessions/:id",
                "POST /api/sessions/:id/msg",
                "DELETE /api/sessions/:id",
                "GET  /api/memory",
                "POST /api/memory/recall",
                "POST /api/memory/remember",
                "GET  /api/skills",
                "POST /api/skills/install",
                "GET  /api/credentials",
                "GET  /api/evolution",
                "GET  /api/swarm",
                "GET  /api/guardian",
                "GET  /api/hud",
            ],
        }


class WebUIRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Web UI."""

    api: WebUIAPI = None  # Set by server

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_DELETE(self):
        self._handle("DELETE")

    def _handle(self, method: str):
        parsed = urlparse(self.path)
        path = parsed.path
        body = {}

        if method in ("POST", "PUT", "PATCH"):
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                raw = self.rfile.read(content_length)
                try:
                    body = json.loads(raw.decode("utf-8"))
                except Exception:
                    body = {"raw": raw.decode("utf-8", errors="replace")}

        result = self.api.handle_request(method, path, body)

        # Serve HTML for root, JSON for API
        if path == "/" or path == "":
            self._serve_html()
        else:
            self._send_json(result)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(
            json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")
        )

    def _serve_html(self):
        try:
            from realtime_hud.dashboard import get_hud

            hud = get_hud()
            hud.collect_from_systems()
            html = hud.render_html()
        except Exception:
            html = "<html><body><h1>OpenClaw v2</h1><p>Dashboard loading...</p></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        pass  # Suppress request logs


class WebUIServer:
    """
    Standalone web UI server.
    Run: python server.py --port 3000
    Then open http://localhost:3000
    """

    def __init__(self, port: int = 3000, host: str = "0.0.0.0"):
        self.port = port
        self.host = host
        self.api = WebUIAPI()
        WebUIRequestHandler.api = self.api

    def start(self):
        server = HTTPServer((self.host, self.port), WebUIRequestHandler)
        print(f"[Web UI] OpenClaw v2 starting on http://localhost:{self.port}")
        print(f"[Web UI] API: http://localhost:{self.port}/api/status")
        print("[Web UI] Press Ctrl+C to stop")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[Web UI] Stopped.")

    def start_background(self) -> threading.Thread:
        def _run():
            server = HTTPServer((self.host, self.port), WebUIRequestHandler)
            server.serve_forever()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t


if __name__ == "__main__":
    import sys

    port = 3000
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])
    server = WebUIServer(port=port)
    server.start()
