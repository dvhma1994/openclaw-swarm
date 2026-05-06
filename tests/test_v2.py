"""
Smoke tests for OpenClaw v2 subsystems.
"""

from openclaw_swarm.v2 import (
    ConstitutionalGuardianV2,
    CredentialPool,
    DualMemorySystem,
    EvolutionEngine,
    HeadlessRunner,
    HUDMetrics,
    PluginManager,
    PromptCompressor,
    RealtimeHUD,
    SelfHealPipeline,
    SessionPersistence,
    SkillsMarketplace,
    StreamingTokenCounter,
    SwarmOrchestrator,
    WebUIServer,
)


class TestV2Imports:
    """Ensure all v2 classes are importable."""

    def test_evolution_engine_import(self):
        assert EvolutionEngine is not None

    def test_swarm_orchestrator_import(self):
        assert SwarmOrchestrator is not None

    def test_dual_memory_import(self):
        assert DualMemorySystem is not None

    def test_credential_pool_import(self):
        assert CredentialPool is not None

    def test_self_heal_pipeline_import(self):
        assert SelfHealPipeline is not None

    def test_hud_import(self):
        assert HUDMetrics is not None
        assert RealtimeHUD is not None

    def test_skills_marketplace_import(self):
        assert SkillsMarketplace is not None

    def test_headless_runner_import(self):
        assert HeadlessRunner is not None

    def test_plugin_manager_import(self):
        assert PluginManager is not None

    def test_prompt_compressor_import(self):
        assert PromptCompressor is not None

    def test_session_persistence_import(self):
        assert SessionPersistence is not None

    def test_streaming_token_counter_import(self):
        assert StreamingTokenCounter is not None

    def test_constitutional_guardian_import(self):
        assert ConstitutionalGuardianV2 is not None

    def test_web_ui_server_import(self):
        assert WebUIServer is not None


class TestV2Smoke:
    """Basic instantiation smoke tests."""

    def test_guardian_instantiation(self):
        g = ConstitutionalGuardianV2()
        assert g is not None

    def test_credential_pool_instantiation(self):
        cp = CredentialPool()
        assert cp is not None

    def test_dual_memory_instantiation(self):
        dm = DualMemorySystem()
        assert dm is not None

    def test_evolution_engine_instantiation(self):
        ee = EvolutionEngine()
        assert ee is not None

    def test_skills_marketplace_instantiation(self):
        sm = SkillsMarketplace()
        assert sm is not None

    def test_prompt_compressor_instantiation(self):
        pc = PromptCompressor()
        assert pc is not None

    def test_streaming_token_counter_instantiation(self):
        stc = StreamingTokenCounter()
        assert stc is not None

    def test_self_heal_pipeline_instantiation(self):
        sh = SelfHealPipeline()
        assert sh is not None

    def test_hud_metrics_instantiation(self):
        hm = HUDMetrics()
        assert hm is not None

    def test_web_ui_server_instantiation(self):
        server = WebUIServer(port=39999)
        assert server is not None


class TestV2CoreSmoke:
    """Smoke tests for openclaw_v2_core entry point."""

    def test_openclaw_v2_core_import(self):
        from openclaw_swarm.v2.core import OpenClawV2

        assert OpenClawV2 is not None

    def test_openclaw_v2_singleton(self):
        from openclaw_swarm.v2.core import get_openclaw_v2, OpenClawV2

        instance = get_openclaw_v2()
        assert isinstance(instance, OpenClawV2)
