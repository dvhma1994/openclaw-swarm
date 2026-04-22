"""
Tests for Multi-tier Memory
"""

import shutil
import tempfile

import pytest

from openclaw_swarm.multi_tier_memory import (
    EpisodicMemory,
    MultiTierMemory,
    SemanticMemory,
    WorkingMemory,
)


class TestWorkingMemory:
    """Test Working Memory"""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_working_memory_init(self, temp_storage):
        """Test initialization"""
        wm = WorkingMemory(temp_storage)
        assert wm.CAPACITY == 7
        assert len(wm.items) == 0

    def test_add_item(self, temp_storage):
        """Test adding items"""
        wm = WorkingMemory(temp_storage)

        item_id = wm.add("Test content")
        assert item_id is not None
        assert len(wm.items) == 1

    def test_capacity_limit(self, temp_storage):
        """Test capacity limit (Miller's law)"""
        wm = WorkingMemory(temp_storage)

        # Add more than capacity
        for i in range(10):
            wm.add(f"Content {i}")

        assert len(wm.items) <= wm.CAPACITY

    def test_get_item(self, temp_storage):
        """Test getting item"""
        wm = WorkingMemory(temp_storage)

        item_id = wm.add("Test content")
        content = wm.get(item_id)

        assert content == "Test content"

    def test_priority_sorting(self, temp_storage):
        """Test priority sorting"""
        wm = WorkingMemory(temp_storage)

        wm.add("Low priority", priority=1)
        wm.add("High priority", priority=10)
        wm.add("Medium priority", priority=5)

        items = wm.get_all()
        assert items[0].priority == 10
        assert items[-1].priority == 1

    def test_clear(self, temp_storage):
        """Test clearing"""
        wm = WorkingMemory(temp_storage)

        wm.add("Content 1")
        wm.add("Content 2")
        wm.clear()

        assert len(wm.items) == 0


class TestEpisodicMemory:
    """Test Episodic Memory"""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_episodic_memory_init(self, temp_storage):
        """Test initialization"""
        em = EpisodicMemory(temp_storage)
        assert len(em.items) == 0

    def test_store_event(self, temp_storage):
        """Test storing event"""
        em = EpisodicMemory(temp_storage)

        item_id = em.store(
            event="Test event",
            participants=["agent1", "agent2"],
            context="Testing",
            outcome="Success",
            importance=0.8,
        )

        assert item_id is not None
        assert len(em.items) == 1

    def test_search_events(self, temp_storage):
        """Test searching events"""
        em = EpisodicMemory(temp_storage)

        em.store("Task A completed", ["agent1"], "Context", "Success", tags=["task"])
        em.store("Task B failed", ["agent2"], "Context", "Fail", tags=["task"])

        results = em.search(query="Task")
        assert len(results) == 2

    def test_get_important(self, temp_storage):
        """Test getting important memories"""
        em = EpisodicMemory(temp_storage)

        em.store("Important event", ["agent"], "Ctx", "Success", importance=0.9)
        em.store("Less important", ["agent"], "Ctx", "Success", importance=0.3)

        important = em.get_important(min_importance=0.7)
        assert len(important) == 1

    def test_tag_filtering(self, temp_storage):
        """Test tag filtering"""
        em = EpisodicMemory(temp_storage)

        em.store("Event 1", [], "Ctx", "Out", tags=["important", "code"])
        em.store("Event 2", [], "Ctx", "Out", tags=["review"])

        results = em.search(tags=["important"])
        assert len(results) == 1


class TestSemanticMemory:
    """Test Semantic Memory"""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_semantic_memory_init(self, temp_storage):
        """Test initialization"""
        sm = SemanticMemory(temp_storage)
        assert len(sm.items) == 0

    def test_store_knowledge(self, temp_storage):
        """Test storing knowledge"""
        sm = SemanticMemory(temp_storage)

        item_id = sm.store(
            concept="Python",
            knowledge="Python is a programming language",
            source_ids=["ep1", "ep2"],
            confidence=0.9,
        )

        assert item_id is not None
        assert len(sm.items) == 1

    def test_find_concept(self, temp_storage):
        """Test finding concept"""
        sm = SemanticMemory(temp_storage)

        sm.store("API Design", "REST APIs use HTTP", ["s1"])

        item = sm.find_concept("API Design")
        assert item is not None
        assert item.concept == "API Design"

    def test_search_knowledge(self, temp_storage):
        """Test searching knowledge"""
        sm = SemanticMemory(temp_storage)

        sm.store("Python", "Language", [], confidence=0.9)
        sm.store("JavaScript", "Language", [], confidence=0.8)

        results = sm.search("language")
        assert len(results) == 2

    def test_update_existing(self, temp_storage):
        """Test updating existing concept"""
        sm = SemanticMemory(temp_storage)

        sm.store("Python", "Initial", [], confidence=0.5)
        sm.store("Python", "Updated", [], confidence=0.7)

        item = sm.find_concept("Python")
        assert item.knowledge == "Updated"
        assert len(sm.items) == 1


class TestMultiTierMemory:
    """Test Complete Multi-tier System"""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_multi_tier_init(self, temp_storage):
        """Test initialization"""
        mtm = MultiTierMemory(temp_storage)

        assert mtm.working is not None
        assert mtm.episodic is not None
        assert mtm.semantic is not None

    def test_add_to_working(self, temp_storage):
        """Test adding to working memory"""
        mtm = MultiTierMemory(temp_storage)

        item_id = mtm.add_to_working("Current task")
        assert item_id is not None

    def test_store_event(self, temp_storage):
        """Test storing event"""
        mtm = MultiTierMemory(temp_storage)

        item_id = mtm.store_event(
            event="Task completed",
            participants=["agent"],
            context="Testing",
            outcome="Success",
        )

        assert item_id is not None

    def test_recall_from_all_tiers(self, temp_storage):
        """Test recalling from all tiers"""
        mtm = MultiTierMemory(temp_storage)

        mtm.add_to_working("Working content")
        mtm.store_event("Episodic event", [], "Ctx", "Success", tags=["test"])
        mtm.semantic.store("Semantic", "Knowledge", [])

        results = mtm.recall("test")

        assert "working" in results
        assert "episodic" in results
        assert "semantic" in results

    def test_get_stats(self, temp_storage):
        """Test getting statistics"""
        mtm = MultiTierMemory(temp_storage)

        mtm.add_to_working("Content 1")
        mtm.store_event("Event 1", [], "Ctx", "Success")
        mtm.semantic.store("Concept 1", "Knowledge", [])

        stats = mtm.get_stats()

        assert stats["working"]["count"] >= 1
        assert stats["episodic"]["count"] >= 1
        assert stats["semantic"]["count"] >= 1

    def test_compression(self, temp_storage):
        """Test compression from episodic to semantic"""
        mtm = MultiTierMemory(temp_storage)

        # Store multiple events with same tag
        for i in range(5):
            mtm.store_event(
                event=f"Code task {i}",
                participants=["coder"],
                context="Coding",
                outcome="Success",
                tags=["coding", "development"],
            )

        # Run compression
        result = mtm.run_compression()

        assert result["compressed"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
