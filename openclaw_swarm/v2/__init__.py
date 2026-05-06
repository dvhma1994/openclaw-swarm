"""OpenClaw Swarm V2 — Advanced AI Agent System.

V2 extends the base swarm system with:
- Evolution Engine: Pattern detection, mutation, fitness evaluation
- Swarm Orchestrator: Multi-agent parallel execution with consensus voting
- Dual Memory System: Automatic (RAG) + Conscious (tagged, importance-scored) + Knowledge Graph
- Credential Pool: API key rotation with failover on 429/401/402
- Auto-Heal Pipeline: lint → fix → re-lint loop
- Real-time HUD: Terminal + HTML dashboard with 50+ metrics
- Skills Marketplace: Searchable/installable skill catalog
- Headless/CI Mode: Full agent loop without UI
- Plugin System: 8 hook points for extensible behavior
- Prompt Compression: 4 strategies (snip/micro/time/priority)
- Session Persistence: Save/restore/checkpoint/branch search
- Streaming Token Counter: Model-specific token estimation + budget
- Constitutional Guardian V2: Drift detection, reputation, budget enforcement
"""

__version__ = "2.0.0"

from openclaw_swarm.v2.auto_heal import SelfHealPipeline
from openclaw_swarm.v2.guardian import ConstitutionalGuardianV2
from openclaw_swarm.v2.credential_pool import CredentialPool
from openclaw_swarm.v2.dual_memory import DualMemorySystem
from openclaw_swarm.v2.evolution_engine import EvolutionEngine
from openclaw_swarm.v2.headless_mode import HeadlessRunner
from openclaw_swarm.v2.plugin_system import PluginManager
from openclaw_swarm.v2.prompt_compressor import PromptCompressor
from openclaw_swarm.v2.realtime_hud import HUDMetrics, RealtimeHUD
from openclaw_swarm.v2.session_persistence import SessionPersistence
from openclaw_swarm.v2.skills_marketplace import SkillsMarketplace
from openclaw_swarm.v2.streaming_token_counter import StreamingTokenCounter
from openclaw_swarm.v2.swarm_orchestrator import SwarmOrchestrator
from openclaw_swarm.v2.web_ui import WebUIServer

__all__ = [
    "EvolutionEngine",
    "SwarmOrchestrator",
    "DualMemorySystem",
    "CredentialPool",
    "SelfHealPipeline",
    "HUDMetrics",
    "RealtimeHUD",
    "SkillsMarketplace",
    "HeadlessRunner",
    "PluginManager",
    "PromptCompressor",
    "SessionPersistence",
    "StreamingTokenCounter",
    "ConstitutionalGuardianV2",
    "WebUIServer",
]
