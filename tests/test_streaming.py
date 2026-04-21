"""
Tests for Streaming functionality
"""

import pytest
import time
from openclaw_swarm.streaming import (
    StreamState,
    StreamChunk,
    StreamManager,
    StreamGenerator,
    TokenCounter,
    ProgressTracker,
    RateLimiter
)


class TestStreamState:
    """Test StreamState enum"""
    
    def test_stream_states_exist(self):
        """Test all stream states exist"""
        assert StreamState.IDLE.value == "idle"
        assert StreamState.STREAMING.value == "streaming"
        assert StreamState.PAUSED.value == "paused"
        assert StreamState.COMPLETED.value == "completed"
        assert StreamState.ERROR.value == "error"


class TestStreamChunk:
    """Test StreamChunk dataclass"""
    
    def test_chunk_creation(self):
        """Test creating a chunk"""
        chunk = StreamChunk(content="Hello", is_final=False)
        
        assert chunk.content == "Hello"
        assert chunk.is_final is False
        assert chunk.metadata == {}
    
    def test_chunk_with_metadata(self):
        """Test chunk with metadata"""
        chunk = StreamChunk(
            content="Hello",
            is_final=True,
            metadata={"tokens": 5}
        )
        
        assert chunk.content == "Hello"
        assert chunk.is_final is True
        assert chunk.metadata["tokens"] == 5


class TestStreamManager:
    """Test StreamManager class"""
    
    def test_manager_initialization(self):
        """Test manager initialization"""
        manager = StreamManager()
        
        assert manager.state == StreamState.IDLE
        assert manager.buffer == []
    
    def test_start_streaming(self):
        """Test starting stream"""
        manager = StreamManager()
        manager.start()
        
        assert manager.state == StreamState.STREAMING
        assert manager.buffer == []
    
    def test_add_chunk(self):
        """Test adding chunks"""
        manager = StreamManager()
        manager.start()
        
        manager.add_chunk("Hello ")
        manager.add_chunk("World!")
        
        assert manager.get_buffer() == "Hello World!"
    
    def test_complete_stream(self):
        """Test completing stream"""
        manager = StreamManager()
        manager.start()
        manager.add_chunk("Hello")
        manager.complete()
        
        assert manager.state == StreamState.COMPLETED
    
    def test_error_stream(self):
        """Test error state"""
        manager = StreamManager()
        manager.start()
        manager.error("Something went wrong")
        
        assert manager.state == StreamState.ERROR
        assert "ERROR: Something went wrong" in manager.get_buffer()
    
    def test_pause_resume(self):
        """Test pause and resume"""
        manager = StreamManager()
        manager.start()
        manager.pause()
        
        assert manager.state == StreamState.PAUSED
        
        manager.resume()
        assert manager.state == StreamState.STREAMING
    
    def test_callback(self):
        """Test chunk callback"""
        chunks = []
        
        def on_chunk(chunk: StreamChunk):
            chunks.append(chunk)
        
        manager = StreamManager(on_chunk=on_chunk)
        manager.start()
        manager.add_chunk("Hello")
        
        assert len(chunks) == 1
        assert chunks[0].content == "Hello"


class TestTokenCounter:
    """Test TokenCounter class"""
    
    def test_counter_initialization(self):
        """Test counter initialization"""
        counter = TokenCounter()
        
        assert counter.total_tokens == 0
        assert counter.total_chunks == 0
    
    def test_add_chunk(self):
        """Test adding chunks"""
        counter = TokenCounter()
        counter.start()
        
        counter.add_chunk("Hello World")
        
        assert counter.total_tokens == 2  # "Hello", "World"
        assert counter.total_chunks == 1
    
    def test_get_stats(self):
        """Test getting statistics"""
        counter = TokenCounter()
        counter.start()
        
        counter.add_chunk("Hello")
        counter.add_chunk("World")
        
        stats = counter.get_stats()
        
        assert stats["total_tokens"] == 2
        assert stats["total_chunks"] == 2
        assert stats["elapsed_seconds"] >= 0


class TestProgressTracker:
    """Test ProgressTracker class"""
    
    def test_tracker_initialization(self):
        """Test tracker initialization"""
        tracker = ProgressTracker(total_steps=100)
        
        assert tracker.total_steps == 100
        assert tracker.current_step == 0
    
    def test_update_progress(self):
        """Test updating progress"""
        tracker = ProgressTracker(total_steps=100)
        
        tracker.update(50)
        
        assert tracker.current_step == 50
        assert tracker.get_progress() == 50.0
    
    def test_advance_progress(self):
        """Test advancing progress"""
        tracker = ProgressTracker(total_steps=100)
        
        tracker.advance(10)
        tracker.advance(20)
        
        assert tracker.current_step == 30
        assert tracker.get_remaining() == 70
    
    def test_complete(self):
        """Test completing progress"""
        tracker = ProgressTracker(total_steps=100)
        
        tracker.complete()
        
        assert tracker.current_step == 100
        assert tracker.get_progress() == 100.0
    
    def test_progress_callback(self):
        """Test progress callback"""
        updates = []
        
        def on_progress(step: int, message: str):
            updates.append((step, message))
        
        tracker = ProgressTracker(total_steps=100, on_progress=on_progress)
        
        tracker.advance(10, "Step 1")
        tracker.advance(20, "Step 2")
        
        assert len(updates) == 2
        assert updates[0] == (10, "Step 1")
        assert updates[1] == (30, "Step 2")


class TestRateLimiter:
    """Test RateLimiter class"""
    
    def test_limiter_initialization(self):
        """Test limiter initialization"""
        limiter = RateLimiter(max_tokens_per_second=100)
        
        assert limiter.max_tokens_per_second == 100
        assert limiter.tokens_this_second == 0
    
    def test_add_tokens(self):
        """Test adding tokens within limit"""
        limiter = RateLimiter(max_tokens_per_second=100)
        
        limiter.wait_if_needed(50)
        
        assert limiter.tokens_this_second == 50
    
    def test_rate_limit_enforcement(self):
        """Test rate limit enforcement"""
        limiter = RateLimiter(max_tokens_per_second=10)
        
        # Should not wait
        limiter.wait_if_needed(5)
        
        # This might trigger wait
        limiter.wait_if_needed(10)
        
        # Check that tokens were counted
        assert limiter.tokens_this_second <= limiter.max_tokens_per_second