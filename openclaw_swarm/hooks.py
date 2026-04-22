"""
OpenClaw Swarm - Hooks System
Lifecycle hooks for agents, tools, and events
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class HookType(Enum):
    """Hook types for different lifecycle events"""

    # Agent lifecycle
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_ERROR = "agent_error"

    # Tool lifecycle
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"

    # Memory lifecycle
    MEMORY_STORE = "memory_store"
    MEMORY_RETRIEVE = "memory_retrieve"

    # Experience lifecycle
    EXPERIENCE_RECORD = "experience_record"
    EXPERIENCE_LEARN = "experience_learn"

    # Swarm lifecycle
    SWARM_START = "swarm_start"
    SWARM_END = "swarm_end"
    SWARM_TASK_START = "swarm_task_start"
    SWARM_TASK_END = "swarm_task_end"

    # Session lifecycle
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # Custom
    CUSTOM = "custom"


@dataclass
class HookContext:
    """Context passed to hook functions"""

    hook_type: HookType
    agent_name: str = ""
    tool_name: str = ""
    timestamp: datetime = None
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class HookResult:
    """Result from hook execution"""

    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    modified_data: Dict[str, Any] = field(default_factory=dict)


class Hook:
    """A single hook with its callback"""

    def __init__(
        self,
        name: str,
        hook_type: HookType,
        callback: Callable[[HookContext], HookResult],
        priority: int = 0,
        enabled: bool = True,
    ):
        self.name = name
        self.hook_type = hook_type
        self.callback = callback
        self.priority = priority
        self.enabled = enabled
        self.call_count = 0
        self.last_call_time = None
        self.total_duration_ms = 0

    def execute(self, context: HookContext) -> HookResult:
        """Execute the hook"""
        if not self.enabled:
            return HookResult(success=True, data={"skipped": True})

        start_time = time.time()

        try:
            result = self.callback(context)

            # Update stats
            self.call_count += 1
            self.last_call_time = datetime.now()
            self.total_duration_ms += (time.time() - start_time) * 1000

            return result

        except Exception as e:
            return HookResult(success=False, error=str(e))


class HookManager:
    """Manage all hooks in the system"""

    def __init__(self):
        self.hooks: Dict[HookType, List[Hook]] = {}
        self._lock = False  # Prevent modifications during execution

    def register(
        self,
        name: str,
        hook_type: HookType,
        callback: Callable[[HookContext], HookResult],
        priority: int = 0,
    ) -> Hook:
        """
        Register a new hook

        Args:
            name: Hook name
            hook_type: Type of hook
            callback: Function to call
            priority: Higher priority = executed first

        Returns:
            The registered hook
        """
        hook = Hook(
            name=name, hook_type=hook_type, callback=callback, priority=priority
        )

        if hook_type not in self.hooks:
            self.hooks[hook_type] = []

        self.hooks[hook_type].append(hook)

        # Sort by priority (descending)
        self.hooks[hook_type].sort(key=lambda h: h.priority, reverse=True)

        return hook

    def unregister(self, name: str) -> bool:
        """
        Unregister a hook by name

        Args:
            name: Hook name to unregister

        Returns:
            True if hook was found and removed
        """
        for hook_type, hooks in self.hooks.items():
            for i, hook in enumerate(hooks):
                if hook.name == name:
                    hooks.pop(i)
                    return True
        return False

    def enable(self, name: str) -> bool:
        """Enable a hook"""
        for hooks in self.hooks.values():
            for hook in hooks:
                if hook.name == name:
                    hook.enabled = True
                    return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a hook"""
        for hooks in self.hooks.values():
            for hook in hooks:
                if hook.name == name:
                    hook.enabled = False
                    return True
        return False

    def execute(self, hook_type: HookType, context: HookContext) -> List[HookResult]:
        """
        Execute all hooks of a type

        Args:
            hook_type: Type of hooks to execute
            context: Context to pass to hooks

        Returns:
            List of results from all hooks
        """
        results = []

        if hook_type not in self.hooks:
            return results

        for hook in self.hooks[hook_type]:
            result = hook.execute(context)
            results.append(result)

            # If a hook fails, we can choose to stop or continue
            # Here we continue to execute all hooks

        return results

    def get_hooks(self, hook_type: Optional[HookType] = None) -> List[Hook]:
        """
        Get all registered hooks

        Args:
            hook_type: Optional filter by type

        Returns:
            List of hooks
        """
        if hook_type:
            return self.hooks.get(hook_type, [])

        all_hooks = []
        for hooks in self.hooks.values():
            all_hooks.extend(hooks)

        return all_hooks

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about hooks"""
        stats = {"total_hooks": 0, "total_calls": 0, "by_type": {}}

        for hook_type, hooks in self.hooks.items():
            type_stats = {
                "count": len(hooks),
                "total_calls": sum(h.call_count for h in hooks),
                "avg_duration_ms": 0,
            }

            if hooks:
                type_stats["avg_duration_ms"] = sum(
                    h.total_duration_ms for h in hooks
                ) / len(hooks)

            stats["by_type"][hook_type.value] = type_stats
            stats["total_hooks"] += len(hooks)
            stats["total_calls"] += type_stats["total_calls"]

        return stats


# Decorator for easy hook registration
def on_event(hook_type: HookType, priority: int = 0):
    """
    Decorator to register a function as a hook

    Usage:
        @on_event(HookType.AGENT_START)
        def my_hook(context: HookContext) -> HookResult:
            print(f"Agent {context.agent_name} started")
            return HookResult(success=True)
    """

    def decorator(func: Callable[[HookContext], HookResult]):
        # Store metadata on function
        func._hook_type = hook_type
        func._hook_priority = priority
        return func

    return decorator


class HookBuilder:
    """Builder for creating hooks with fluent API"""

    def __init__(self, manager: HookManager):
        self.manager = manager
        self._name = ""
        self._hook_type = None
        self._callback = None
        self._priority = 0

    def name(self, name: str) -> "HookBuilder":
        """Set hook name"""
        self._name = name
        return self

    def type(self, hook_type: HookType) -> "HookBuilder":
        """Set hook type"""
        self._hook_type = hook_type
        return self

    def callback(self, callback: Callable[[HookContext], HookResult]) -> "HookBuilder":
        """Set callback function"""
        self._callback = callback
        return self

    def priority(self, priority: int) -> "HookBuilder":
        """Set priority"""
        self._priority = priority
        return self

    def build(self) -> Hook:
        """Build and register the hook"""
        if not self._name:
            raise ValueError("Hook name is required")
        if not self._hook_type:
            raise ValueError("Hook type is required")
        if not self._callback:
            raise ValueError("Callback is required")

        return self.manager.register(
            name=self._name,
            hook_type=self._hook_type,
            callback=self._callback,
            priority=self._priority,
        )
