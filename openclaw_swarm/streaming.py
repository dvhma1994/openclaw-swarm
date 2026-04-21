"""
OpenClaw Swarm - Streaming Support
Real-time token output and streaming responses
"""

import time
import threading
from typing import Callable, Optional, Generator, Any
from dataclasses import dataclass
from enum import Enum


class StreamState(Enum):
    """Stream state"""
    IDLE = "idle"
    STREAMING = "streaming"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StreamChunk:
    """A chunk of streaming data"""
    content: str
    is_final: bool = False
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StreamManager:
    """Manage streaming responses"""
    
    def __init__(self, on_chunk: Optional[Callable[[StreamChunk], None]] = None):
        self.state = StreamState.IDLE
        self.buffer = []
        self.on_chunk = on_chunk
        self._lock = threading.Lock()
    
    def start(self):
        """Start streaming"""
        with self._lock:
            self.state = StreamState.STREAMING
            self.buffer = []
    
    def pause(self):
        """Pause streaming"""
        with self._lock:
            self.state = StreamState.PAUSED
    
    def resume(self):
        """Resume streaming"""
        with self._lock:
            if self.state == StreamState.PAUSED:
                self.state = StreamState.STREAMING
    
    def complete(self):
        """Complete streaming"""
        with self._lock:
            self.state = StreamState.COMPLETED
    
    def error(self, error_msg: str):
        """Set error state"""
        with self._lock:
            self.state = StreamState.ERROR
            self.buffer.append(f"ERROR: {error_msg}")
    
    def add_chunk(self, content: str, is_final: bool = False, metadata: dict = None):
        """Add a chunk to the stream"""
        with self._lock:
            if self.state == StreamState.STREAMING:
                chunk = StreamChunk(
                    content=content,
                    is_final=is_final,
                    metadata=metadata or {}
                )
                self.buffer.append(content)
                
                if self.on_chunk:
                    self.on_chunk(chunk)
                
                if is_final:
                    self.state = StreamState.COMPLETED
    
    def get_buffer(self) -> str:
        """Get current buffer content"""
        with self._lock:
            return "".join(self.buffer)
    
    def get_state(self) -> StreamState:
        """Get current state"""
        return self.state
    
    def is_streaming(self) -> bool:
        """Check if streaming is active"""
        return self.state == StreamState.STREAMING


class StreamGenerator:
    """Generate streaming responses"""
    
    def __init__(self, model: str, call_fn: Callable):
        self.model = model
        self.call_fn = call_fn
    
    def stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """
        Stream response from model
        
        Args:
            prompt: The prompt to send
            **kwargs: Additional arguments
            
        Yields:
            Chunks of the response
        """
        # Call model with stream=True
        response = self.call_fn(prompt, stream=True, **kwargs)
        
        for chunk in response:
            yield chunk
    
    def stream_to_callback(self, prompt: str, callback: Callable[[str], None], **kwargs):
        """
        Stream response to a callback function
        
        Args:
            prompt: The prompt to send
            callback: Function to call with each chunk
            **kwargs: Additional arguments
        """
        for chunk in self.stream(prompt, **kwargs):
            callback(chunk)
    
    def collect(self, prompt: str, **kwargs) -> str:
        """
        Collect all chunks into a single response
        
        Args:
            prompt: The prompt to send
            **kwargs: Additional arguments
            
        Returns:
            Complete response
        """
        return "".join(self.stream(prompt, **kwargs))


class TokenCounter:
    """Count tokens in streaming responses"""
    
    def __init__(self):
        self.total_tokens = 0
        self.total_chunks = 0
        self.start_time = None
        self._lock = threading.Lock()
    
    def start(self):
        """Start counting"""
        with self._lock:
            self.total_tokens = 0
            self.total_chunks = 0
            self.start_time = time.time()
    
    def add_chunk(self, chunk: str):
        """Add a chunk and count tokens"""
        with self._lock:
            # Simple whitespace-based token counting
            tokens = len(chunk.split())
            self.total_tokens += tokens
            self.total_chunks += 1
    
    def get_stats(self) -> dict:
        """Get statistics"""
        with self._lock:
            elapsed = time.time() - self.start_time if self.start_time else 0
            
            return {
                "total_tokens": self.total_tokens,
                "total_chunks": self.total_chunks,
                "elapsed_seconds": elapsed,
                "tokens_per_second": self.total_tokens / elapsed if elapsed > 0 else 0,
                "chunks_per_second": self.total_chunks / elapsed if elapsed > 0 else 0
            }


class ProgressTracker:
    """Track progress during long operations"""
    
    def __init__(self, total_steps: int = 100, on_progress: Optional[Callable[[int, str], None]] = None):
        self.total_steps = total_steps
        self.current_step = 0
        self.on_progress = on_progress
        self._lock = threading.Lock()
    
    def update(self, step: int, message: str = ""):
        """Update progress"""
        with self._lock:
            self.current_step = min(step, self.total_steps)
            
            if self.on_progress:
                self.on_progress(self.current_step, message)
    
    def advance(self, steps: int = 1, message: str = ""):
        """Advance progress by steps"""
        with self._lock:
            self.current_step = min(self.current_step + steps, self.total_steps)
            
            if self.on_progress:
                self.on_progress(self.current_step, message)
    
    def complete(self):
        """Mark as complete"""
        with self._lock:
            self.current_step = self.total_steps
            
            if self.on_progress:
                self.on_progress(self.total_steps, "Complete")
    
    def get_progress(self) -> float:
        """Get progress as percentage"""
        return (self.current_step / self.total_steps) * 100
    
    def get_remaining(self) -> int:
        """Get remaining steps"""
        return self.total_steps - self.current_step


class RateLimiter:
    """Rate limiter for streaming responses"""
    
    def __init__(self, max_tokens_per_second: int = 100):
        self.max_tokens_per_second = max_tokens_per_second
        self.tokens_this_second = 0
        self.last_reset = time.time()
        self._lock = threading.Lock()
    
    def wait_if_needed(self, token_count: int):
        """Wait if rate limit exceeded"""
        with self._lock:
            now = time.time()
            
            # Reset counter every second
            if now - self.last_reset >= 1.0:
                self.tokens_this_second = 0
                self.last_reset = now
            
            # Check if we need to wait
            if self.tokens_this_second + token_count > self.max_tokens_per_second:
                wait_time = 1.0 - (now - self.last_reset)
                if wait_time > 0:
                    time.sleep(wait_time)
                    self.tokens_this_second = 0
                    self.last_reset = time.time()
            
            self.tokens_this_second += token_count