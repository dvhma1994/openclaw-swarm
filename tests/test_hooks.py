"""
Tests for Hooks functionality
"""

import pytest
from openclaw_swarm.hooks import (
    HookType,
    HookContext,
    HookResult,
    Hook,
    HookManager,
    on_event,
    HookBuilder,
)


class TestHookType:
    """Test HookType enum"""

    def test_hook_types_exist(self):
        """Test all hook types exist"""
        assert HookType.AGENT_START.value == "agent_start"
        assert HookType.AGENT_END.value == "agent_end"
        assert HookType.AGENT_ERROR.value == "agent_error"
        assert HookType.TOOL_START.value == "tool_start"
        assert HookType.TOOL_END.value == "tool_end"
        assert HookType.TOOL_ERROR.value == "tool_error"
        assert HookType.MEMORY_STORE.value == "memory_store"
        assert HookType.MEMORY_RETRIEVE.value == "memory_retrieve"
        assert HookType.EXPERIENCE_RECORD.value == "experience_record"
        assert HookType.EXPERIENCE_LEARN.value == "experience_learn"
        assert HookType.SWARM_START.value == "swarm_start"
        assert HookType.SWARM_END.value == "swarm_end"
        assert HookType.SWARM_TASK_START.value == "swarm_task_start"
        assert HookType.SWARM_TASK_END.value == "swarm_task_end"
        assert HookType.SESSION_START.value == "session_start"
        assert HookType.SESSION_END.value == "session_end"
        assert HookType.CUSTOM.value == "custom"


class TestHookContext:
    """Test HookContext dataclass"""

    def test_context_creation(self):
        """Test creating a context"""
        context = HookContext(hook_type=HookType.AGENT_START)

        assert context.hook_type == HookType.AGENT_START
        assert context.agent_name == ""
        assert context.tool_name == ""
        assert context.data == {}
        assert context.metadata == {}

    def test_context_with_data(self):
        """Test context with data"""
        context = HookContext(
            hook_type=HookType.TOOL_START,
            agent_name="Coder",
            tool_name="bash",
            data={"command": "ls -la"},
            metadata={"priority": "high"},
        )

        assert context.hook_type == HookType.TOOL_START
        assert context.agent_name == "Coder"
        assert context.tool_name == "bash"
        assert context.data["command"] == "ls -la"
        assert context.metadata["priority"] == "high"


class TestHookResult:
    """Test HookResult dataclass"""

    def test_result_creation(self):
        """Test creating a result"""
        result = HookResult(success=True)

        assert result.success is True
        assert result.data == {}
        assert result.error is None
        assert result.modified_data == {}

    def test_result_with_error(self):
        """Test result with error"""
        result = HookResult(success=False, error="Something went wrong")

        assert result.success is False
        assert result.error == "Something went wrong"


class TestHook:
    """Test Hook class"""

    def test_hook_creation(self):
        """Test creating a hook"""

        def callback(context: HookContext) -> HookResult:
            return HookResult(success=True)

        hook = Hook(
            name="test_hook",
            hook_type=HookType.AGENT_START,
            callback=callback,
            priority=0,
        )

        assert hook.name == "test_hook"
        assert hook.hook_type == HookType.AGENT_START
        assert hook.priority == 0
        assert hook.enabled is True
        assert hook.call_count == 0

    def test_hook_execute(self):
        """Test hook execution"""

        def callback(context: HookContext) -> HookResult:
            return HookResult(success=True, data={"executed": True})

        hook = Hook(name="test_hook", hook_type=HookType.AGENT_START, callback=callback)

        context = HookContext(hook_type=HookType.AGENT_START)
        result = hook.execute(context)

        assert result.success is True
        assert result.data["executed"] is True
        assert hook.call_count == 1

    def test_hook_disabled(self):
        """Test disabled hook"""

        def callback(context: HookContext) -> HookResult:
            return HookResult(success=True)

        hook = Hook(
            name="test_hook",
            hook_type=HookType.AGENT_START,
            callback=callback,
            enabled=False,
        )

        context = HookContext(hook_type=HookType.AGENT_START)
        result = hook.execute(context)

        assert result.success is True
        assert result.data["skipped"] is True
        assert hook.call_count == 0  # Not executed


class TestHookManager:
    """Test HookManager class"""

    def test_manager_initialization(self):
        """Test manager initialization"""
        manager = HookManager()

        assert manager.hooks == {}

    def test_register_hook(self):
        """Test registering a hook"""
        manager = HookManager()

        def callback(context: HookContext) -> HookResult:
            return HookResult(success=True)

        hook = manager.register(
            name="test_hook", hook_type=HookType.AGENT_START, callback=callback
        )

        assert hook.name == "test_hook"
        assert HookType.AGENT_START in manager.hooks
        assert len(manager.hooks[HookType.AGENT_START]) == 1

    def test_unregister_hook(self):
        """Test unregistering a hook"""
        manager = HookManager()

        def callback(context: HookContext) -> HookResult:
            return HookResult(success=True)

        manager.register("test_hook", HookType.AGENT_START, callback)
        result = manager.unregister("test_hook")

        assert result is True
        assert len(manager.hooks[HookType.AGENT_START]) == 0

    def test_enable_disable_hook(self):
        """Test enabling and disabling hooks"""
        manager = HookManager()

        def callback(context: HookContext) -> HookResult:
            return HookResult(success=True)

        manager.register("test_hook", HookType.AGENT_START, callback)

        # Disable
        result = manager.disable("test_hook")
        assert result is True

        hook = manager.hooks[HookType.AGENT_START][0]
        assert hook.enabled is False

        # Enable
        result = manager.enable("test_hook")
        assert result is True
        assert hook.enabled is True

    def test_execute_hooks(self):
        """Test executing hooks"""
        manager = HookManager()

        results = []

        def callback1(context: HookContext) -> HookResult:
            results.append("hook1")
            return HookResult(success=True)

        def callback2(context: HookContext) -> HookResult:
            results.append("hook2")
            return HookResult(success=True)

        manager.register("hook1", HookType.AGENT_START, callback1, priority=1)
        manager.register("hook2", HookType.AGENT_START, callback2, priority=0)

        context = HookContext(hook_type=HookType.AGENT_START)
        manager.execute(HookType.AGENT_START, context)

        # Higher priority should execute first
        assert results == ["hook1", "hook2"]

    def test_get_hooks(self):
        """Test getting hooks"""
        manager = HookManager()

        def callback(context: HookContext) -> HookResult:
            return HookResult(success=True)

        manager.register("hook1", HookType.AGENT_START, callback)
        manager.register("hook2", HookType.AGENT_END, callback)

        all_hooks = manager.get_hooks()
        assert len(all_hooks) == 2

        agent_hooks = manager.get_hooks(HookType.AGENT_START)
        assert len(agent_hooks) == 1

    def test_get_stats(self):
        """Test getting statistics"""
        manager = HookManager()

        def callback(context: HookContext) -> HookResult:
            return HookResult(success=True)

        manager.register("hook1", HookType.AGENT_START, callback)
        manager.register("hook2", HookType.AGENT_END, callback)

        context = HookContext(hook_type=HookType.AGENT_START)
        manager.execute(HookType.AGENT_START, context)

        stats = manager.get_stats()

        assert stats["total_hooks"] == 2
        assert stats["total_calls"] == 1
        assert "agent_start" in stats["by_type"]


class TestHookDecorator:
    """Test hook decorator"""

    def test_on_event_decorator(self):
        """Test on_event decorator"""

        @on_event(HookType.AGENT_START)
        def my_hook(context: HookContext) -> HookResult:
            return HookResult(success=True)

        assert hasattr(my_hook, "_hook_type")
        assert my_hook._hook_type == HookType.AGENT_START


class TestHookBuilder:
    """Test HookBuilder class"""

    def test_builder(self):
        """Test using builder"""
        manager = HookManager()

        def callback(context: HookContext) -> HookResult:
            return HookResult(success=True)

        hook = (
            HookBuilder(manager)
            .name("test_hook")
            .type(HookType.AGENT_START)
            .callback(callback)
            .priority(10)
            .build()
        )

        assert hook.name == "test_hook"
        assert hook.hook_type == HookType.AGENT_START
        assert hook.priority == 10

    def test_builder_missing_name(self):
        """Test builder with missing name"""
        manager = HookManager()

        def callback(context: HookContext) -> HookResult:
            return HookResult(success=True)

        builder = HookBuilder(manager).type(HookType.AGENT_START).callback(callback)

        with pytest.raises(ValueError, match="Hook name is required"):
            builder.build()

    def test_builder_missing_type(self):
        """Test builder with missing type"""
        manager = HookManager()

        def callback(context: HookContext) -> HookResult:
            return HookResult(success=True)

        builder = HookBuilder(manager).name("test_hook").callback(callback)

        with pytest.raises(ValueError, match="Hook type is required"):
            builder.build()

    def test_builder_missing_callback(self):
        """Test builder with missing callback"""
        manager = HookManager()

        builder = HookBuilder(manager).name("test_hook").type(HookType.AGENT_START)

        with pytest.raises(ValueError, match="Callback is required"):
            builder.build()
