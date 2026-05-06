"""
Integration Tests - End-to-end testing
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from openclaw_swarm import (
    Anonymizer,
    ExperienceDB,
    Memory,
    MultiTierMemory,
    Orchestrator,
    Router,
    SwarmCoordinator,
)


def _ollama_available():
    try:
        import ollama

        ollama.list()
        return True
    except Exception:
        return False


# Skip tests that require Ollama when it is not running
requires_ollama = pytest.mark.skipif(
    not _ollama_available(),
    reason="Requires Ollama which is not running",
)


class TestIntegration:
    """End-to-end integration tests"""

    @pytest.fixture
    def temp_dir(self):
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    @requires_ollama
    def test_full_workflow(self, temp_dir):
        """Test complete workflow from task to result"""
        # Initialize components
        memory = MultiTierMemory(temp_dir)
        experience = ExperienceDB(temp_dir)
        coordinator = SwarmCoordinator(
            storage_path=temp_dir, memory=Memory(temp_dir), experience=experience
        )

        # Run a task
        result = coordinator.run_swarm(
            "Explain what Python is", max_workers=2, decompose=False
        )

        assert result is not None
        assert "final_result" in result

        # Check memory was stored
        memory.add_to_working("Test task", priority=5)
        assert len(memory.working.items) >= 1

        # Check experience was recorded
        experience.record_experience(
            task_type="general",
            context="Test",
            action_taken="Explain",
            result="Success",
            success=True,
        )
        assert len(experience.experiences) >= 1

        # Get stats
        stats = coordinator.get_status()
        assert "agents" in stats
        assert "memory_stats" in stats

    def test_memory_pipeline(self, temp_dir):
        """Test memory pipeline from working to semantic"""
        mtm = MultiTierMemory(temp_dir)

        # Add to working memory
        mtm.add_to_working("Current task: API development", priority=8)

        # Store event in episodic
        mtm.store_event(
            event="Completed API",
            participants=["Coder"],
            context="REST API development",
            outcome="Success",
            importance=0.8,
            tags=["api", "coding"],
        )

        # Run compression
        mtm.run_compression()

        # Recall from all tiers
        recall = mtm.recall("API")

        assert len(recall["working"]) >= 1
        assert len(recall["episodic"]) >= 1

        # Get stats
        stats = mtm.get_stats()
        assert stats["working"]["count"] >= 1
        assert stats["episodic"]["count"] >= 1

    @requires_ollama
    def test_anonymizer_integration(self, temp_dir):
        """Test anonymizer with other components"""
        anon = Anonymizer()
        coordinator = SwarmCoordinator(storage_path=temp_dir)

        # Anonymize before sending to swarm
        text = "Contact john@example.com for help"
        result = anon.anonymize(text)

        assert "john@example.com" not in result.anonymized
        assert len(result.entities) >= 1

        # Process through swarm
        task_result = coordinator.run_swarm(
            "Explain this text: " + result.anonymized, decompose=False
        )

        assert task_result is not None

        # De-anonymize response if needed
        anon.de_anonymize(task_result["final_result"], result.mapping)
        # Should work without crashing

    def test_experience_learning_loop(self, temp_dir):
        """Test experience learning improves over time"""
        exp = ExperienceDB(temp_dir)

        # Record successes
        for i in range(5):
            exp.record_experience(
                task_type="coding",
                context=f"Task {i}",
                action_taken="Used FastAPI",
                result="Success",
                success=True,
            )

        # Record failures
        for i in range(2):
            exp.record_experience(
                task_type="coding",
                context=f"Task {i}",
                action_taken="Used raw Python",
                result="Failed",
                success=False,
            )

        # Get advice
        advice = exp.get_advice("coding")

        # Should have some advice (either best practices or warnings)
        assert len(advice["best_practices"]) + len(advice["warnings"]) > 0

        # Check confidence for approach
        should_try, reason = exp.should_try_approach("coding", "FastAPI")
        # May or may not recommend based on confidence threshold
        assert isinstance(should_try, bool)
        assert isinstance(reason, str)

    @requires_ollama
    def test_router_memory_integration(self, temp_dir):
        """Test router with memory"""
        router = Router()
        memory = Memory(temp_dir)

        # Use router
        response = router.call("Hello")

        # Store in memory
        memory.store(
            agent="Router",
            task="chat",
            input_data="Hello",
            output_data=response[:100],
            success=True,
        )

        # Search memory
        results = memory.search_by_task("chat")
        assert len(results) >= 1

        # Get stats
        stats = memory.get_stats()
        assert stats["total_memories"] >= 1

    def test_orchestrator_with_experience(self, temp_dir):
        """Test orchestrator learns from experience"""
        orch = Orchestrator()
        exp = ExperienceDB(temp_dir)

        # Run task
        results = orch.run_workflow("Explain Python", workflow=["researcher"])

        # Record experience
        for agent_id, result in results.items():
            exp.record_experience(
                task_type=agent_id,
                context="Explain Python",
                action_taken=f"Processed with {result.agent_name}",
                result=result.output[:50],
                success=result.success,
            )

        # Get advice for future tasks
        advice = exp.get_advice("researcher")

        # Should have some advice
        assert advice is not None

    @requires_ollama
    def test_swarm_with_memory(self, temp_dir):
        """Test swarm with memory"""
        coordinator = SwarmCoordinator(storage_path=temp_dir, memory=Memory(temp_dir))

        # Run task
        result = coordinator.run_swarm("What is 2+2?", decompose=False)

        assert result["completed"] >= 1

        # Get status
        status = coordinator.get_status()
        assert "agents" in status

    def test_plugin_system_integration(self, temp_dir):
        """Test plugin system"""
        from openclaw_swarm.plugins import PluginManager

        pm = PluginManager(temp_dir)

        # Create plugin template
        plugin_path = pm.create_plugin_template("test_agent", "agent")
        assert Path(plugin_path).exists()

        # Load plugin
        loaded = pm.load_plugin("test_agent")
        assert loaded is True

        # Check stats
        stats = pm.get_stats()
        assert stats["total_plugins"] == 1
        assert stats["enabled_plugins"] == 1

    @requires_ollama
    def test_full_system_integration(self, temp_dir):
        """Test full system integration"""
        # Initialize all components
        memory = MultiTierMemory(temp_dir)
        experience = ExperienceDB(temp_dir)
        anon = Anonymizer()
        coordinator = SwarmCoordinator(
            storage_path=temp_dir, memory=Memory(temp_dir), experience=experience
        )

        # Anonymize input
        text = "Email me at test@example.com"
        anon_result = anon.anonymize(text)

        # Store in working memory
        memory.add_to_working(anon_result.anonymized, priority=7)

        # Process through swarm
        result = coordinator.run_swarm(
            f"Explain: {anon_result.anonymized}", decompose=False
        )

        # Record experience
        experience.record_experience(
            task_type="explanation",
            context=anon_result.anonymized,
            action_taken="Processed",
            result=(
                result["final_result"][:50]
                if result.get("final_result")
                else "No result"
            ),
            success=True,
        )

        # Store event in episodic
        memory.store_event(
            event="Processed explanation",
            participants=["Swarm"],
            context="Integration test",
            outcome="Success",
            importance=0.7,
        )

        # Run compression
        memory.run_compression()

        # Get all stats
        memory_stats = memory.get_stats()
        exp_stats = experience.get_stats()
        swarm_stats = coordinator.get_status()

        assert memory_stats["working"]["count"] >= 1
        assert memory_stats["episodic"]["count"] >= 1
        assert exp_stats["total_experiences"] >= 1
        assert "agents" in swarm_stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
