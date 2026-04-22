"""
Real-time HUD Dashboard - Terminal & HTML
=========================================
Inspired by: Claude HUD (statusline), MassGen (live TUI), OpenClaw observability.

Generates live terminal status lines and HTML dashboards showing:
- Context window usage with color-coded bars
- Tool activity (reads, edits, searches)
- Agent tracking (running subagents, models, elapsed time)
- Budget / cost tracking per session
- Task/todo progress
- Evolution engine generation & stats
- Swarm orchestrator status
- Memory system stats
- Credential pool health

Output formats:
1. Terminal status line (2-3 lines, like Claude HUD)
2. HTML dashboard (auto-refresh, full stats)
3. JSON API (for programmatic access)
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BASE_DIR = Path(
    os.environ.get(
        "OPENCLAW_DIRECTOR_DIR", Path.home() / ".openclaw" / "workspaces" / "director"
    )
)
HUD_DIR = BASE_DIR / "realtime_hud"
HUD_DIR.mkdir(parents=True, exist_ok=True)
DASHBOARD_FILE = BASE_DIR / "dashboards" / "live_hud.html"


@dataclass
class HUDMetrics:
    """All metrics displayed in the HUD."""

    # Context
    context_used_pct: float = 0.0
    context_total: int = 0
    context_used: int = 0
    # Model
    model_name: str = ""
    provider: str = ""
    # Session
    session_duration_min: float = 0.0
    session_id: str = ""
    # Tools
    tool_reads: int = 0
    tool_edits: int = 0
    tool_searches: int = 0
    tool_bash: int = 0
    tool_writes: int = 0
    tool_mcp: int = 0
    # Agents
    active_agents: list = field(default_factory=list)
    # Cost
    total_cost_usd: float = 0.0
    daily_budget_usd: float = 10.0
    daily_used_usd: float = 0.0
    # Tokens
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    # Todo
    todo_total: int = 0
    todo_completed: int = 0
    # Evolution
    evolution_generation: int = 0
    evolution_mutations: int = 0
    evolution_promotions: int = 0
    # Swarm
    swarm_agents: int = 0
    swarm_tasks: int = 0
    # Memory
    memory_auto_entries: int = 0
    memory_conscious_entries: int = 0
    memory_kg_nodes: int = 0
    # Credentials
    cred_active: int = 0
    cred_total: int = 0
    # Git
    git_branch: str = ""
    git_dirty: bool = False
    # Timestamp
    updated_at: str = ""

    def to_dict(self):
        return asdict(self)


class RealtimeHUD:
    """Generates terminal & HTML HUD displays."""

    def __init__(self):
        self.metrics = HUDMetrics()

    def update(self, **kwargs):
        """Update HUD metrics."""
        for k, v in kwargs.items():
            if hasattr(self.metrics, k):
                setattr(self.metrics, k, v)
        self.metrics.updated_at = datetime.now(timezone.utc).isoformat()

    def collect_from_systems(self):
        """Auto-collect metrics from all connected systems."""
        # Evolution Engine
        try:
            from evolution_engine.engine import get_evolution_engine

            e = get_evolution_engine().get_stats()
            self.metrics.evolution_generation = e.get("generation", 0)
            self.metrics.evolution_mutations = e.get("total_mutations", 0)
            self.metrics.evolution_promotions = e.get("total_promotions", 0)
        except Exception:
            pass

        # Swarm
        try:
            from swarm_orchestrator.orchestrator import get_swarm

            s = get_swarm().get_stats()
            self.metrics.swarm_agents = s.get("registered_agents", 0)
            self.metrics.swarm_tasks = s.get("total_tasks", 0)
        except Exception:
            pass

        # Memory
        try:
            from dual_memory.memory import get_dual_memory

            m = get_dual_memory().get_stats()
            self.metrics.memory_auto_entries = m.get("automatic", {}).get(
                "total_entries", 0
            )
            self.metrics.memory_conscious_entries = m.get("conscious", {}).get(
                "total_entries", 0
            )
            self.metrics.memory_kg_nodes = m.get("knowledge_graph", {}).get("nodes", 0)
        except Exception:
            pass

        # Credentials
        try:
            from credential_pool.pool import get_credential_pool

            c = get_credential_pool().get_stats()
            self.metrics.cred_active = c.get("total_active", 0)
            self.metrics.cred_total = c.get("total_keys", 0)
        except Exception:
            pass

        # Git
        try:
            import subprocess

            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                timeout=5,
                shell=True,
                windows_hide=True,
            )
            if result.returncode == 0:
                self.metrics.git_branch = result.stdout.decode().strip()
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                timeout=5,
                shell=True,
                windows_hide=True,
            )
            self.metrics.git_dirty = bool(result.stdout.strip())
        except Exception:
            pass

        self.metrics.updated_at = datetime.now(timezone.utc).isoformat()

    def render_terminal(self) -> str:
        """Render 2-3 line terminal HUD (like Claude HUD)."""
        ctx_pct = self.metrics.context_used_pct
        ctx_bar = self._bar(ctx_pct, 20)
        budget_pct = (
            self.metrics.daily_used_usd / max(self.metrics.daily_budget_usd, 0.01)
        ) * 100
        budget_bar = self._bar(budget_pct, 10)

        line1 = (
            f"[{self.metrics.model_name or 'unknown'}] "
            f"{self.metrics.provider} | "
            f"{self.metrics.git_branch}"
            f"{'*' if self.metrics.git_dirty else ''}"
        )

        line2 = (
            f"Context {ctx_bar} {ctx_pct:.0f}% | "
            f"Budget {budget_bar} ${self.metrics.daily_used_usd:.2f}/${self.metrics.daily_budget_usd:.0f}"
        )

        tools_str = ""
        if self.metrics.tool_reads:
            tools_str += f"R:{self.metrics.tool_reads} "
        if self.metrics.tool_edits:
            tools_str += f"E:{self.metrics.tool_edits} "
        if self.metrics.tool_searches:
            tools_str += f"S:{self.metrics.tool_searches} "
        if self.metrics.tool_bash:
            tools_str += f"B:{self.metrics.tool_bash}"

        line3 = ""
        if tools_str:
            line3 += f"Tools: {tools_str}"
        if self.metrics.active_agents:
            agents = ", ".join(self.metrics.active_agents[:3])
            line3 += f" | Agents: {agents}"
        if self.metrics.todo_total > 0:
            line3 += f" | Todo: {self.metrics.todo_completed}/{self.metrics.todo_total}"
        if self.metrics.evolution_generation > 0:
            line3 += f" | Evo: Gen {self.metrics.evolution_generation}"

        output = f"{line1}\n{line2}"
        if line3:
            output += f"\n{line3}"
        return output

    def render_json(self) -> str:
        return json.dumps(self.metrics.to_dict(), indent=2, default=str)

    def render_html(self) -> str:
        """Render full HTML dashboard with auto-refresh."""
        m = self.metrics
        budget_pct = (m.daily_used_usd / max(m.daily_budget_usd, 0.01)) * 100
        return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenClaw HUD</title>
<meta http-equiv="refresh" content="30">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'JetBrains Mono',monospace; background:#0d1117; color:#c9d1d9; padding:20px; }}
  .hud {{ max-width:1200px; margin:0 auto; }}
  .header {{ display:flex; justify-content:space-between; align-items:center;
             padding:15px 20px; background:#161b22; border-radius:8px; margin-bottom:15px;
             border:1px solid #30363d; }}
  .header h1 {{ font-size:20px; color:#58a6ff; }}
  .header .model {{ color:#7ee787; font-size:14px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
           gap:12px; }}
  .card {{ background:#161b22; border:1px solid #30363d; border-radius:8px;
           padding:16px; }}
  .card h3 {{ color:#58a6ff; margin-bottom:10px; font-size:14px; }}
  .bar {{ height:12px; background:#21262d; border-radius:6px; overflow:hidden; }}
  .bar-fill {{ height:100%; border-radius:6px; transition:width 0.5s; }}
  .bar-green {{ background:#238636; }}
  .bar-yellow {{ background:#d29922; }}
  .bar-red {{ background:#da3633; }}
  .stat {{ display:flex; justify-content:space-between; padding:4px 0;
           font-size:13px; border-bottom:1px solid #21262d; }}
  .stat .label {{ color:#8b949e; }}
  .stat .value {{ color:#c9d1d9; font-weight:600; }}
  .agents {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }}
  .agent-badge {{ background:#1f6feb33; color:#58a6ff; padding:2px 8px;
                  border-radius:4px; font-size:12px; }}
  footer {{ text-align:center; margin-top:20px; color:#484f58; font-size:12px; }}
</style>
</head><body>
<div class="hud">
  <div class="header">
    <div><h1>OpenClaw HUD</h1>
         <span class="model">{m.model_name} | {m.provider}</span></div>
    <div style="text-align:right">
      <div style="font-size:12px;color:#8b949e">Session: {m.session_id or 'N/A'}</div>
      <div style="font-size:12px;color:#8b949e">Duration: {m.session_duration_min:.1f}m</div>
      <div style="font-size:12px;color:#8b949e">Updated: {m.updated_at[:19] if m.updated_at else 'N/A'}</div>
    </div>
  </div>

  <div class="grid">
    <!-- Context Window -->
    <div class="card">
      <h3>Context Window</h3>
      <div class="bar"><div class="bar-fill {self._bar_class(m.context_used_pct)}"
        style="width:{min(m.context_used_pct,100)}%"></div></div>
      <div class="stat"><span class="label">Used</span>
        <span class="value">{m.context_used:,} / {m.context_total:,} ({m.context_used_pct:.1f}%)</span></div>
    </div>

    <!-- Budget -->
    <div class="card">
      <h3>Budget & Cost</h3>
      <div class="bar"><div class="bar-fill {self._bar_class(budget_pct)}"
        style="width:{min(budget_pct,100)}%"></div></div>
      <div class="stat"><span class="label">Daily</span>
        <span class="value">${m.daily_used_usd:.2f} / ${m.daily_budget_usd:.0f}</span></div>
      <div class="stat"><span class="label">Session Total</span>
        <span class="value">${m.total_cost_usd:.4f}</span></div>
      <div class="stat"><span class="label">Tokens</span>
        <span class="value">{m.total_tokens:,} (P:{m.prompt_tokens:,} C:{m.completion_tokens:,})</span></div>
    </div>

    <!-- Tools -->
    <div class="card">
      <h3>Tool Activity</h3>
      <div class="stat"><span class="label">Reads</span><span class="value">{m.tool_reads}</span></div>
      <div class="stat"><span class="label">Edits</span><span class="value">{m.tool_edits}</span></div>
      <div class="stat"><span class="label">Searches</span><span class="value">{m.tool_searches}</span></div>
      <div class="stat"><span class="label">Bash</span><span class="value">{m.tool_bash}</span></div>
      <div class="stat"><span class="label">Writes</span><span class="value">{m.tool_writes}</span></div>
      <div class="stat"><span class="label">MCP</span><span class="value">{m.tool_mcp}</span></div>
    </div>

    <!-- Evolution Engine -->
    <div class="card">
      <h3>Evolution Engine</h3>
      <div class="stat"><span class="label">Generation</span><span class="value">{m.evolution_generation}</span></div>
      <div class="stat"><span class="label">Mutations</span><span class="value">{m.evolution_mutations}</span></div>
      <div class="stat"><span class="label">Promotions</span><span class="value">{m.evolution_promotions}</span></div>
    </div>

    <!-- Swarm -->
    <div class="card">
      <h3>Swarm</h3>
      <div class="stat"><span class="label">Agents</span><span class="value">{m.swarm_agents}</span></div>
      <div class="stat"><span class="label">Tasks</span><span class="value">{m.swarm_tasks}</span></div>
    </div>

    <!-- Memory -->
    <div class="card">
      <h3>Memory</h3>
      <div class="stat"><span class="label">Auto</span><span class="value">{m.memory_auto_entries}</span></div>
      <div class="stat"><span class="label">Conscious</span><span class="value">{m.memory_conscious_entries}</span></div>
      <div class="stat"><span class="label">KG Nodes</span><span class="value">{m.memory_kg_nodes}</span></div>
    </div>

    <!-- Credentials -->
    <div class="card">
      <h3>Credentials</h3>
      <div class="stat"><span class="label">Active / Total</span>
        <span class="value">{m.cred_active} / {m.cred_total}</span></div>
    </div>

    <!-- Todo -->
    <div class="card">
      <h3>Todo Progress</h3>
      <div class="bar"><div class="bar-fill bar-green"
        style="width:{(m.todo_completed/max(m.todo_total,1))*100:.0f}%"></div></div>
      <div class="stat"><span class="label">Completed</span>
        <span class="value">{m.todo_completed} / {m.todo_total}</span></div>
    </div>
  </div>

  <!-- Active Agents -->
  <div class="card" style="margin-top:12px">
    <h3>Active Agents</h3>
    <div class="agents">
      {' '.join(f'<span class="agent-badge">{a}</span>' for a in m.active_agents) if m.active_agents else '<span style="color:#484f58">None active</span>'}
    </div>
  </div>

  <footer>OpenClaw HUD | Auto-refresh: 30s | Git: {m.git_branch}{'*' if m.git_dirty else ''}</footer>
</div>
</body></html>"""

    def save_html(self, path: Path = DASHBOARD_FILE):
        """Save HTML dashboard to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.render_html())
        return str(path)

    def _bar(self, pct: float, width: int = 20) -> str:
        filled = int(pct / 100 * width)
        return "#" * filled + "-" * (width - filled)

    def _bar_class(self, pct: float) -> str:
        if pct < 50:
            return "bar-green"
        elif pct < 80:
            return "bar-yellow"
        return "bar-red"


_hud: Optional[RealtimeHUD] = None


def get_hud() -> RealtimeHUD:
    global _hud
    if _hud is None:
        _hud = RealtimeHUD()
    return _hud


if __name__ == "__main__":
    import sys

    hud = get_hud()
    hud.update(
        model_name="Sonnet 4.6",
        provider="Anthropic",
        context_used_pct=45,
        context_total=200000,
        context_used=90000,
        daily_budget_usd=10,
        daily_used_usd=2.5,
        total_cost_usd=1.23,
        total_tokens=50000,
        tool_reads=12,
        tool_edits=5,
        tool_searches=3,
    )
    hud.collect_from_systems()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "terminal"
    if cmd == "terminal":
        print(hud.render_terminal())
    elif cmd == "json":
        print(hud.render_json())
    elif cmd == "html":
        path = hud.save_html()
        print(f"Dashboard saved: {path}")
    else:
        print("Commands: terminal, json, html")
