"""
Example: Hooks System
======================

This example shows how to use the hooks system for lifecycle events.
"""

from openclaw_swarm import HookManager, HookType, HookContext, HookResult, HookBuilder


def main():
    print("=" * 60)
    print("OpenClaw Swarm - Hooks Example")
    print("=" * 60)

    # 1. Create Hook Manager
    print("\n1. Create Hook Manager")
    print("-" * 40)

    manager = HookManager()
    print(f"Hooks registered: {len(manager.get_hooks())}")

    # 2. Register Hooks
    print("\n2. Register Hooks")
    print("-" * 40)

    # Agent lifecycle hooks
    def on_agent_start(context: HookContext) -> HookResult:
        print(f"[HOOK] Agent starting: {context.agent_name}")
        return HookResult(success=True, data={"started_at": "now"})

    def on_agent_end(context: HookContext) -> HookResult:
        print(f"[HOOK] Agent finished: {context.agent_name}")
        return HookResult(success=True, data={"finished_at": "now"})

    def on_agent_error(context: HookContext) -> HookResult:
        print(f"[HOOK] Agent error: {context.agent_name} - {context.data.get('error')}")
        return HookResult(success=True)

    # Register hooks
    manager.register(
        "agent_start_logger", HookType.AGENT_START, on_agent_start, priority=10
    )
    manager.register("agent_end_logger", HookType.AGENT_END, on_agent_end, priority=10)
    manager.register(
        "agent_error_handler", HookType.AGENT_ERROR, on_agent_error, priority=5
    )

    print(f"Registered {len(manager.get_hooks())} hooks")

    # 3. Execute Hooks
    print("\n3. Execute Hooks")
    print("-" * 40)

    # Execute agent start hooks
    context = HookContext(
        hook_type=HookType.AGENT_START,
        agent_name="Coder",
        data={"task": "Write a function"},
    )

    results = manager.execute(HookType.AGENT_START, context)
    print(f"Executed {len(results)} hooks")

    # Execute agent end hooks
    context = HookContext(
        hook_type=HookType.AGENT_END,
        agent_name="Coder",
        data={"task": "Write a function", "status": "success"},
    )

    results = manager.execute(HookType.AGENT_END, context)
    print(f"Executed {len(results)} hooks")

    # 4. Tool Hooks
    print("\n4. Tool Hooks")
    print("-" * 40)

    def on_tool_start(context: HookContext) -> HookResult:
        print(f"[HOOK] Tool starting: {context.tool_name}")
        print(f"       Command: {context.data.get('command', 'N/A')}")
        return HookResult(success=True)

    def on_tool_end(context: HookContext) -> HookResult:
        print(f"[HOOK] Tool finished: {context.tool_name}")
        print(f"       Duration: {context.data.get('duration', 'N/A')}ms")
        return HookResult(success=True)

    manager.register("tool_start_logger", HookType.TOOL_START, on_tool_start)
    manager.register("tool_end_logger", HookType.TOOL_END, on_tool_end)

    # Execute tool hooks
    context = HookContext(
        hook_type=HookType.TOOL_START,
        agent_name="Coder",
        tool_name="bash",
        data={"command": "npm test"},
    )

    manager.execute(HookType.TOOL_START, context)

    # 5. Memory Hooks
    print("\n5. Memory Hooks")
    print("-" * 40)

    def on_memory_store(context: HookContext) -> HookResult:
        print(f"[HOOK] Storing memory: {context.data.get('key')}")
        return HookResult(success=True)

    def on_memory_retrieve(context: HookContext) -> HookResult:
        print(f"[HOOK] Retrieving memory: {context.data.get('query')}")
        return HookResult(success=True, modified_data={"result": "found"})

    manager.register("memory_store_logger", HookType.MEMORY_STORE, on_memory_store)
    manager.register(
        "memory_retrieve_logger", HookType.MEMORY_RETRIEVE, on_memory_retrieve
    )

    # Execute memory hooks
    context = HookContext(
        hook_type=HookType.MEMORY_STORE,
        data={"key": "task_001", "value": "Write a function"},
    )

    manager.execute(HookType.MEMORY_STORE, context)

    # 6. Swarm Hooks
    print("\n6. Swarm Hooks")
    print("-" * 40)

    def on_swarm_start(context: HookContext) -> HookResult:
        print(f"[HOOK] Swarm starting with {context.data.get('agent_count', 0)} agents")
        return HookResult(success=True)

    def on_swarm_end(context: HookContext) -> HookResult:
        print(f"[HOOK] Swarm completed with status: {context.data.get('status')}")
        return HookResult(success=True)

    manager.register(
        "swarm_start_logger", HookType.SWARM_START, on_swarm_start, priority=20
    )
    manager.register("swarm_end_logger", HookType.SWARM_END, on_swarm_end, priority=20)

    # Execute swarm hooks
    context = HookContext(
        hook_type=HookType.SWARM_START,
        data={"agent_count": 3, "task": "Build a REST API"},
    )

    manager.execute(HookType.SWARM_START, context)

    # 7. Hook Stats
    print("\n7. Hook Statistics")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"Total hooks: {stats['total_hooks']}")
    print(f"Total calls: {stats['total_calls']}")

    for hook_type, type_stats in stats["by_type"].items():
        print(f"\n{hook_type}:")
        print(f"  Count: {type_stats['count']}")
        print(f"  Calls: {type_stats['total_calls']}")

    # 8. Using Hook Builder
    print("\n8. Using Hook Builder")
    print("-" * 40)

    def my_hook(context: HookContext) -> HookResult:
        print(f"[BUILDER HOOK] {context.hook_type.value}")
        return HookResult(success=True)

    hook = (
        HookBuilder(manager)
        .name("builder_hook")
        .type(HookType.CUSTOM)
        .callback(my_hook)
        .priority(5)
        .build()
    )

    print(f"Created hook: {hook.name}")
    print(f"Priority: {hook.priority}")

    # 9. Enable/Disable Hooks
    print("\n9. Enable/Disable Hooks")
    print("-" * 40)

    # Disable a hook
    manager.disable("agent_start_logger")
    print("Disabled agent_start_logger")

    # Enable a hook
    manager.enable("agent_start_logger")
    print("Enabled agent_start_logger")

    # 10. Unregister Hooks
    print("\n10. Unregister Hooks")
    print("-" * 40)

    manager.unregister("agent_error_handler")
    print("Unregistered agent_error_handler")

    remaining = len(manager.get_hooks())
    print(f"Remaining hooks: {remaining}")

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
