"""
Performance Benchmarks for OpenClaw Swarm
"""

import time

import pytest

from openclaw_swarm import (
    Anonymizer,
    ExperienceDB,
    Memory,
    MultiTierMemory,
    Orchestrator,
    Router,
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


class TestPerformance:
    """Performance benchmarks"""

    @requires_ollama
    def test_router_performance(self, benchmark):
        """Benchmark router call"""
        router = Router()

        def call_router():
            return router.call("Hello, what is 2+2?")

        result = benchmark(call_router)
        assert result is not None

    def test_memory_store_performance(self, benchmark):
        """Benchmark memory store"""
        import shutil
        import tempfile

        temp_dir = tempfile.mkdtemp()

        memory = Memory(temp_dir)

        def store_memory():
            return memory.store(
                agent="Test",
                task="Benchmark",
                input_data="Test input",
                output_data="Test output",
                success=True,
            )

        result = benchmark(store_memory)
        assert result is not None

        shutil.rmtree(temp_dir)

    def test_memory_search_performance(self, benchmark):
        """Benchmark memory search"""
        import shutil
        import tempfile

        temp_dir = tempfile.mkdtemp()

        memory = Memory(temp_dir)

        # Store some memories first
        for i in range(100):
            memory.store(
                agent=f"Agent{i % 5}",
                task=f"Task {i}",
                input_data=f"Input {i}",
                output_data=f"Output {i}",
                success=True,
            )

        def search_memory():
            return memory.find_similar("Task", limit=10)

        result = benchmark(search_memory)
        assert len(result) >= 1

        shutil.rmtree(temp_dir)

    def test_experience_record_performance(self, benchmark):
        """Benchmark experience recording"""
        import shutil
        import tempfile

        temp_dir = tempfile.mkdtemp()

        exp = ExperienceDB(temp_dir)

        def record_experience():
            return exp.record_experience(
                task_type="coding",
                context="Test context",
                action_taken="Test action",
                result="Success",
                success=True,
            )

        result = benchmark(record_experience)
        assert result is not None

        shutil.rmtree(temp_dir)

    def test_anonymizer_performance(self, benchmark):
        """Benchmark anonymization"""
        anon = Anonymizer()

        text = """
        Contact us at support@example.com or sales@company.org.
        Server IP: 192.168.1.1 and 10.0.0.1
        Phone: 555-123-4567 and +1-800-555-1234
        API keys: sk-abcdef123456789 and api_key_123456789
        Password: password=secret123
        """

        def anonymize_text():
            return anon.anonymize(text)

        result = benchmark(anonymize_text)
        assert "support@example.com" not in result.anonymized

    def test_anonymizer_pii_detection(self, benchmark):
        """Benchmark PII detection"""
        anon = Anonymizer()

        text = "Email: test@example.com, IP: 192.168.1.1, Phone: 555-123-4567"

        def detect_pii():
            return anon.detect_pii(text)

        result = benchmark(detect_pii)
        assert len(result) >= 3

    def test_working_memory_performance(self, benchmark):
        """Benchmark working memory"""
        import shutil
        import tempfile

        temp_dir = tempfile.mkdtemp()

        from openclaw_swarm.multi_tier_memory import WorkingMemory

        wm = WorkingMemory(temp_dir)

        def add_to_working():
            return wm.add("Test content", priority=5)

        result = benchmark(add_to_working)
        assert result is not None

        shutil.rmtree(temp_dir)

    def test_episodic_memory_performance(self, benchmark):
        """Benchmark episodic memory"""
        import shutil
        import tempfile

        temp_dir = tempfile.mkdtemp()

        from openclaw_swarm.multi_tier_memory import EpisodicMemory

        em = EpisodicMemory(temp_dir)

        def store_event():
            return em.store(
                event="Test event",
                participants=["Agent1"],
                context="Test context",
                outcome="Success",
                importance=0.8,
            )

        result = benchmark(store_event)
        assert result is not None

        shutil.rmtree(temp_dir)

    def test_semantic_memory_performance(self, benchmark):
        """Benchmark semantic memory"""
        import shutil
        import tempfile

        temp_dir = tempfile.mkdtemp()

        from openclaw_swarm.multi_tier_memory import SemanticMemory

        sm = SemanticMemory(temp_dir)

        def store_knowledge():
            return sm.store(
                concept="Python",
                knowledge="Programming language",
                source_ids=["ep1", "ep2"],
                confidence=0.9,
            )

        result = benchmark(store_knowledge)
        assert result is not None

        shutil.rmtree(temp_dir)

    def test_multi_tier_memory_recalls(self, benchmark):
        """Benchmark multi-tier memory recall"""
        import shutil
        import tempfile

        temp_dir = tempfile.mkdtemp()

        mtm = MultiTierMemory(temp_dir)

        # Add some data
        mtm.add_to_working("Test task")
        mtm.store_event("Test event", [], "Context", "Success")
        mtm.semantic.store("Test", "Knowledge", [])

        def recall():
            return mtm.recall("Test", limit=5)

        result = benchmark(recall)
        assert "working" in result

        shutil.rmtree(temp_dir)

    def test_orchestrator_agent_list(self, benchmark):
        """Benchmark orchestrator agent listing"""
        orch = Orchestrator()

        def list_agents():
            return orch.list_agents()

        result = benchmark(list_agents)
        assert len(result) >= 4

    def test_plugin_manager_stats(self, benchmark):
        """Benchmark plugin manager"""
        import shutil
        import tempfile

        temp_dir = tempfile.mkdtemp()

        from openclaw_swarm.plugins import PluginManager

        pm = PluginManager(temp_dir)

        def get_stats():
            return pm.get_stats()

        result = benchmark(get_stats)
        assert "total_plugins" in result

        shutil.rmtree(temp_dir)


class TestBenchmarks:
    """Run benchmarks and record results"""

    @pytest.fixture
    def temp_dir(self):
        import shutil
        import tempfile

        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    @requires_ollama
    def test_router_latency(self, temp_dir):
        """Test router latency"""
        router = Router()

        # Warm up
        router.call("Hello")

        # Measure
        start = time.time()
        for _ in range(10):
            router.call("What is 2+2?")
        end = time.time()

        avg_latency = (end - start) / 10
        print(f"\nRouter average latency: {avg_latency*1000:.2f}ms")

        # Should be reasonable (< 5 seconds with local LLM)
        assert avg_latency < 5.0

    def test_memory_throughput(self, temp_dir):
        """Test memory throughput"""
        memory = Memory(temp_dir)

        # Measure store throughput
        start = time.time()
        for i in range(100):
            memory.store(
                agent=f"Agent{i % 5}",
                task=f"Task {i}",
                input_data=f"Input {i}" * 10,
                output_data=f"Output {i}" * 10,
                success=True,
            )
        end = time.time()

        throughput = 100 / (end - start)
        print(f"\nMemory store throughput: {throughput:.2f} ops/sec")

        # Should be fast (> 50 ops/sec)
        assert throughput > 50

    def test_experience_learning_speed(self, temp_dir):
        """Test experience learning speed"""
        exp = ExperienceDB(temp_dir)

        # Measure learning speed
        start = time.time()
        for i in range(50):
            exp.record_experience(
                task_type="test",
                context=f"Context {i}",
                action_taken=f"Action {i}",
                result=f"Result {i}",
                success=True,
            )
        end = time.time()

        avg_time = (end - start) / 50
        print(f"\nExperience recording average: {avg_time*1000:.2f}ms")

        # Should be fast (< 50ms per record)
        assert avg_time < 0.05

    def test_anonymizer_speed(self, temp_dir):
        """Test anonymizer speed"""
        anon = Anonymizer()

        text = "Email: test@example.com " * 100

        start = time.time()
        for _ in range(100):
            anon.anonymize(text)
        end = time.time()

        throughput = 100 / (end - start)
        print(f"\nAnonymizer throughput: {throughput:.2f} ops/sec")

        # Should be fast (> 100 ops/sec)
        assert throughput > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
