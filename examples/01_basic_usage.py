"""
Example: Basic Usage
====================

This example shows how to use OpenClaw Swarm for simple tasks.
"""

from openclaw_swarm import (
    Router,
    Orchestrator,
    Memory,
    ExperienceDB,
    Anonymizer,
    SwarmCoordinator,
)


def main():
    print("=" * 60)
    print("OpenClaw Swarm - Basic Usage Example")
    print("=" * 60)
    
    # 1. Router - Auto route to best model
    print("\n1. Router Example")
    print("-" * 40)
    router = Router()
    
    # Detect task type automatically
    task_type = router.detect_task_type("Write a Python function")
    print(f"Task type detected: {task_type.value}")
    
    # Get model for task
    model = router.get_model(task_type)
    print(f"Model selected: {model}")
    
    # 2. Orchestrator - Run multi-agent workflow
    print("\n2. Orchestrator Example")
    print("-" * 40)
    orchestrator = Orchestrator()
    
    # List available agents
    agents = orchestrator.list_agents()
    print(f"Available agents: {agents}")
    
    # 3. Memory - Store and retrieve experiences
    print("\n3. Memory Example")
    print("-" * 40)
    memory = Memory()
    
    # Store a memory
    memory.store(
        agent="Coder",
        task="Create function",
        input_data="User requested fibonacci",
        output_data="def fibonacci(n): ...",
        success=True
    )
    
    # Get stats
    stats = memory.get_stats()
    print(f"Total memories: {stats['total_memories']}")
    print(f"Success rate: {stats['success_rate']:.2%}")
    
    # 4. Experience - Learn from past
    print("\n4. Experience Example")
    print("-" * 40)
    exp = ExperienceDB()
    
    # Record experience
    exp.record_experience(
        task_type="coding",
        context="Creating fibonacci function",
        action_taken="Used iterative approach",
        result="Success - fast and efficient",
        success=True
    )
    
    # Get advice
    advice = exp.get_advice("coding")
    print(f"Best practices: {advice['best_practices']}")
    print(f"Warnings: {advice['warnings']}")
    
    # 5. Anonymizer - Protect PII
    print("\n5. Anonymizer Example")
    print("-" * 40)
    anon = Anonymizer()
    
    text = "Contact me at john@example.com or call 555-123-4567"
    result = anon.anonymize(text)
    
    print(f"Original: {text}")
    print(f"Anonymized: {result.anonymized}")
    print(f"PII found: {len(result.entities)}")
    
    # 6. Swarm - Run coordinated task
    print("\n6. Swarm Example")
    print("-" * 40)
    coordinator = SwarmCoordinator()
    
    # Get status
    status = coordinator.get_status()
    print(f"Agents: {len(status['agents'])}")
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()