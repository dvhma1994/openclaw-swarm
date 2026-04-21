"""
Example: Streaming Support
==========================

This example shows how to use streaming responses.
"""

import time
from openclaw_swarm import StreamManager, StreamChunk, TokenCounter, ProgressTracker


def main():
    print("=" * 60)
    print("OpenClaw Swarm - Streaming Example")
    print("=" * 60)
    
    # 1. Stream Manager
    print("\n1. Stream Manager")
    print("-" * 40)
    
    chunks_received = []
    
    def on_chunk(chunk: StreamChunk):
        chunks_received.append(chunk)
        print(f"Received: {chunk.content}", end="", flush=True)
    
    manager = StreamManager(on_chunk=on_chunk)
    manager.start()
    
    # Simulate streaming
    words = ["Hello", " ", "World", "!"]
    for word in words:
        manager.add_chunk(word)
        time.sleep(0.1)
    
    manager.complete()
    
    print(f"\nTotal chunks: {len(chunks_received)}")
    print(f"Buffer: {manager.get_buffer()}")
    
    # 2. Token Counter
    print("\n2. Token Counter")
    print("-" * 40)
    
    counter = TokenCounter()
    counter.start()
    
    counter.add_chunk("Hello World")
    counter.add_chunk("This is a test")
    counter.add_chunk("Streaming is cool")
    
    stats = counter.get_stats()
    
    print(f"Total tokens: {stats['total_tokens']}")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Elapsed: {stats['elapsed_seconds']:.2f}s")
    print(f"Tokens/sec: {stats['tokens_per_second']:.2f}")
    
    # 3. Progress Tracker
    print("\n3. Progress Tracker")
    print("-" * 40)
    
    progress_updates = []
    
    def on_progress(step: int, message: str):
        progress_updates.append((step, message))
        print(f"Progress: {step}% - {message}")
    
    tracker = ProgressTracker(total_steps=100, on_progress=on_progress)
    
    tracker.advance(25, "Step 1 complete")
    tracker.advance(25, "Step 2 complete")
    tracker.advance(25, "Step 3 complete")
    tracker.complete()
    
    print(f"Final progress: {tracker.get_progress():.1f}%")
    print(f"Total updates: {len(progress_updates)}")
    
    # 4. Rate Limiter
    print("\n4. Rate Limiter")
    print("-" * 40)
    
    from openclaw_swarm import RateLimiter
    
    limiter = RateLimiter(max_tokens_per_second=100)
    
    limiter.wait_if_needed(50)
    print("Added 50 tokens")
    
    limiter.wait_if_needed(30)
    print("Added 30 more tokens")
    
    print(f"Current tokens this second: {limiter.tokens_this_second}")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()