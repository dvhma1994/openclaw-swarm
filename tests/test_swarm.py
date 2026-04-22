"""
Tests for OpenClaw Swarm
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from openclaw_swarm.experience import ExperienceDB
from openclaw_swarm.memory import Memory
from openclaw_swarm.orchestrator import Orchestrator
from openclaw_swarm.router import Router, TaskType


class TestMemory:
    """Test Memory system"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_memory_init(self, temp_storage):
        """Test memory initialization"""
        memory = Memory(temp_storage)
        assert memory.storage_path == Path(temp_storage)
        assert len(memory.memories) == 0

    def test_store_memory(self, temp_storage):
        """Test storing a memory"""
        memory = Memory(temp_storage)

        entry_id = memory.store(
            agent="Coder",
            task="Write function",
            input_data="Create fibonacci",
            output_data="def fib(n): ...",
            success=True,
        )

        assert entry_id is not None
        assert len(memory.memories) == 1
        assert "Coder" in memory.index["by_agent"]

    def test_search_by_agent(self, temp_storage):
        """Test searching by agent"""
        memory = Memory(temp_storage)

        memory.store("Coder", "task1", "input1", "output1", True)
        memory.store("Planner", "task2", "input2", "output2", True)
        memory.store("Coder", "task3", "input3", "output3", True)

        results = memory.search_by_agent("Coder")
        assert len(results) == 2

    def test_find_similar(self, temp_storage):
        """Test finding similar memories"""
        memory = Memory(temp_storage)

        memory.store("Coder", "fibonacci", "Create fib function", "def fib...", True)
        memory.store("Coder", "sorting", "Create sort function", "def sort...", True)

        results = memory.find_similar("fibonacci")
        assert len(results) >= 1
        assert (
            "fib" in results[0].task.lower() or "fib" in results[0].input_data.lower()
        )

    def test_memory_stats(self, temp_storage):
        """Test memory statistics"""
        memory = Memory(temp_storage)

        memory.store("Coder", "task1", "input", "output", True)
        memory.store("Coder", "task2", "input", "output", False)

        stats = memory.get_stats()
        assert stats["total_memories"] == 2
        assert stats["successful"] == 1
        assert stats["failed"] == 1
        assert 0 < stats["success_rate"] <= 1


class TestExperience:
    """Test Experience system"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_experience_init(self, temp_storage):
        """Test experience initialization"""
        exp = ExperienceDB(temp_storage)
        assert exp.storage_path == Path(temp_storage)
        assert len(exp.experiences) == 0

    def test_record_experience(self, temp_storage):
        """Test recording an experience"""
        exp = ExperienceDB(temp_storage)

        exp_id = exp.record_experience(
            task_type="coding",
            context="Create API",
            action_taken="Used FastAPI",
            result="Success",
            success=True,
        )

        assert exp_id is not None
        assert len(exp.experiences) == 1
        assert len(exp.lessons) > 0  # Should extract a lesson

    def test_get_advice(self, temp_storage):
        """Test getting advice"""
        exp = ExperienceDB(temp_storage)

        # Record some experiences
        exp.record_experience("coding", "API", "Used FastAPI", "Success", True)
        exp.record_experience("coding", "API", "Used Flask", "Failed", False)
        exp.record_experience("coding", "API", "Used FastAPI", "Success", True)

        advice = exp.get_advice("coding")

        assert isinstance(advice, dict)
        assert "best_practices" in advice
        assert "warnings" in advice

    def test_should_try_approach(self, temp_storage):
        """Test should try approach"""
        exp = ExperienceDB(temp_storage)

        # Record experiences
        exp.record_experience("coding", "API", "FastAPI", "Success", True)
        exp.record_experience("coding", "API", "Bad approach", "Failed", False)

        # Check approach
        should_try, reason = exp.should_try_approach("coding", "FastAPI")
        assert should_try is True

        should_try, reason = exp.should_try_approach("coding", "Bad approach")
        # May or may not recommend based on confidence
        assert isinstance(should_try, bool)
        assert isinstance(reason, str)

    def test_experience_stats(self, temp_storage):
        """Test experience statistics"""
        exp = ExperienceDB(temp_storage)

        exp.record_experience("coding", "task", "action1", "result1", True)
        exp.record_experience("coding", "task", "action2", "result2", False)
        exp.record_experience("review", "task", "action3", "result3", True)

        stats = exp.get_stats()
        assert stats["total_experiences"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1


class TestRouter:
    """Test Router system"""

    def test_router_init(self):
        """Test router initialization"""
        router = Router()
        assert router.config is not None
        assert len(router.models) > 0

    def test_detect_task_type(self):
        """Test task type detection"""
        router = Router()

        # Coding task
        assert router.detect_task_type("Write a Python function") == TaskType.CODING

        # Reasoning task
        assert router.detect_task_type("Why does this happen?") == TaskType.REASONING

        # Arabic task (if Arabic chars present)
        arabic_text = "مرحبا بك في العالم"
        assert router.detect_task_type(arabic_text) == TaskType.ARABIC

        # Chat task
        assert router.detect_task_type("Hello, how are you?") == TaskType.CHAT

    def test_get_model(self):
        """Test model selection"""
        router = Router()

        model = router.get_model(TaskType.CODING)
        assert model is not None
        assert isinstance(model, str)

        fallback = router.get_fallback_model(TaskType.CODING)
        assert fallback is not None


class TestOrchestrator:
    """Test Orchestrator system"""

    def test_orchestrator_init(self):
        """Test orchestrator initialization"""
        orch = Orchestrator()
        assert orch.config is not None
        assert len(orch.agents) > 0

    def test_list_agents(self):
        """Test listing agents"""
        orch = Orchestrator()
        agents = orch.list_agents()

        assert "planner" in agents
        assert "coder" in agents
        assert "reviewer" in agents

    def test_get_agent(self):
        """Test getting agent"""
        orch = Orchestrator()

        planner = orch.get_agent("planner")
        assert planner is not None
        assert planner.name == "Planner"

        nonexistent = orch.get_agent("nonexistent")
        assert nonexistent is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
