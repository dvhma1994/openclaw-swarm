"""
Example: Provider Management
=============================

This example shows how to manage AI provider profiles.
"""

import os

from openclaw_swarm import ProviderManager, AgentRouter


def main():
    print("=" * 60)
    print("OpenClaw Swarm - Provider Management Example")
    print("=" * 60)

    # 1. Create provider manager
    print("\n1. Create Provider Manager")
    print("-" * 40)

    manager = ProviderManager()
    print(f"Profiles loaded: {len(manager.list_profiles())}")

    # 2. Create Ollama profile
    print("\n2. Create Ollama Profile")
    print("-" * 40)

    ollama_profile = manager.create_ollama_profile()
    manager.add_profile(ollama_profile)

    print(f"Name: {ollama_profile.name}")
    print(f"Type: {ollama_profile.provider_type.value}")
    print(f"Base URL: {ollama_profile.base_url}")
    print(f"Default Model: {ollama_profile.default_model}")
    print(f"Models: {ollama_profile.models}")

    # 3. Create OpenAI profile (needs API key)
    print("\n3. Create OpenAI Profile")
    print("-" * 40)

    openai_profile = manager.create_openai_profile(os.environ.get("OPENAI_API_KEY", ""))
    print(f"Name: {openai_profile.name}")
    print(f"Type: {openai_profile.provider_type.value}")
    print(f"Base URL: {openai_profile.base_url}")
    print(f"Capabilities: {openai_profile.capabilities}")
    print(f"Supports Vision: {openai_profile.supports_vision}")

    # 4. List all profiles
    print("\n4. List All Profiles")
    print("-" * 40)

    for name in manager.list_profiles():
        profile = manager.get_profile(name)
        if profile:
            print(f"- {name}: {profile.default_model}")

    # 5. Set active profile
    print("\n5. Set Active Profile")
    print("-" * 40)

    manager.set_active("ollama")
    active = manager.get_active()

    if active:
        print(f"Active profile: {active.name}")
        print(f"Default model: {active.default_model}")

    # 6. Agent Router - Route agents to specific models
    print("\n6. Agent Router")
    print("-" * 40)

    router = AgentRouter()

    # Set routing for specific agents
    router.set_routing("planner", "phi4:14b")
    router.set_routing("coder", "qwen2.5:7b")
    router.set_routing("reviewer", "phi4:14b")

    print(f"Default model: {router.default_model}")
    print("Routing:")
    for agent, model in router.routing.items():
        print(f"  {agent} -> {model}")

    # 7. Get model for agent
    print("\n7. Get Model for Agent")
    print("-" * 40)

    print(f"Planner model: {router.get_model('planner')}")
    print(f"Coder model: {router.get_model('coder')}")
    print(f"Unknown agent model: {router.get_model('unknown')}")

    # 8. Save and load routing configuration
    print("\n8. Save Routing Configuration")
    print("-" * 40)

    routing_config = router.to_dict()
    print(f"Config: {routing_config}")

    # Reconstruct from dict
    new_router = AgentRouter.from_dict(routing_config)
    print(f"Reconstructed default: {new_router.default_model}")

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
