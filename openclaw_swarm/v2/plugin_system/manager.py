"""
Plugin System Manager — Inspired by OpenClaude plugins + Antigravity Skills.
Manages installable plugins that extend OpenClaw v2 capabilities.

Plugin Lifecycle:
  Discovery -> Install -> Enable -> Hook Registration -> Active -> Disable -> Uninstall

Hook Points:
  - pre_prompt:   Before a prompt is sent to the LLM
  - post_response: After a response is received
  - pre_tool:     Before a tool is executed
  - post_tool:    After a tool returns
  - pre_commit:   Before a git commit
  - on_startup:   When OpenClaw starts
  - on_shutdown:  When OpenClaw shuts down
  - on_error:     When an error occurs
  - on_drift:     When drift is detected

Each plugin declares:
  - Metadata (name, version, author, description)
  - Required permissions
  - Enabled hook points and their handlers
  - Configuration schema
  - Dependencies on other plugins
"""

import hashlib
import json
import logging
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional

BASE_DIR = Path(
    os.environ.get(
        "OPENCLAW_DIRECTOR_DIR", Path.home() / ".openclaw" / "workspaces" / "director"
    )
)
PLUGIN_DIR = BASE_DIR / "plugin_system"
PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
PLUGINS_REGISTRY = PLUGIN_DIR / "registry.json"
PLUGINS_INSTALLED = PLUGIN_DIR / "installed"
PLUGINS_INSTALLED.mkdir(parents=True, exist_ok=True)


class PluginState(str, Enum):
    DISCOVERED = "discovered"
    INSTALLED = "installed"
    ENABLED = "enabled"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


class HookPoint(str, Enum):
    PRE_PROMPT = "pre_prompt"
    POST_RESPONSE = "post_response"
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    PRE_COMMIT = "pre_commit"
    ON_STARTUP = "on_startup"
    ON_SHUTDOWN = "on_shutdown"
    ON_ERROR = "on_error"
    ON_DRIFT = "on_drift"


class PluginPermission(str, Enum):
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    NETWORK = "network"
    SHELL = "shell"
    MEMORY = "memory"
    TELEGRAM = "telegram"
    GIT = "git"


@dataclass
class PluginManifest:
    """Plugin metadata and configuration."""

    plugin_id: str
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    hooks: list = field(default_factory=list)  # List of HookPoint values
    permissions: list = field(default_factory=list)
    config_schema: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)
    dependencies: list = field(default_factory=list)  # plugin_ids
    source: str = "local"
    source_url: str = ""
    state: PluginState = PluginState.DISCOVERED
    install_path: str = ""
    error: str = ""
    installed_at: str = ""
    enabled_at: str = ""

    def to_dict(self):
        return {**asdict(self), "state": self.state.value}

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        data["state"] = PluginState(data.get("state", "discovered"))
        return cls(**data)


@dataclass
class HookContext:
    """Context passed to hook handlers."""

    hook_point: str
    plugin_id: str
    data: dict = field(default_factory=dict)
    result: Any = None
    proceed: bool = True  # False = block the action
    modified_data: dict = field(default_factory=dict)
    error: str = ""


class PluginManager:
    """
    Manages the full plugin lifecycle: discover, install, enable, hook, disable.
    """

    def __init__(self, registry_path: Path = PLUGINS_REGISTRY):
        self.registry_path = registry_path
        self.plugins: Dict[str, PluginManifest] = {}
        self.hooks: Dict[str, Dict[str, Callable]] = (
            {}
        )  # hook_point -> {plugin_id: handler}
        self._load()

    def _load(self):
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for pdata in data.get("plugins", []):
                    plugin = PluginManifest.from_dict(pdata)
                    self.plugins[plugin.plugin_id] = plugin
            except Exception:
                logging.exception("Failed to load plugin registry")

    def _save(self):
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(self.registry_path.parent), suffix=".tmp"
        )
        try:
            data = {
                "plugins": [p.to_dict() for p in self.plugins.values()],
                "count": len(self.plugins),
                "updated": datetime.now(timezone.utc).isoformat(),
            }
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            os.replace(tmp_path, str(self.registry_path))
        except Exception:
            logging.exception("Failed to save plugin registry")
            os.unlink(tmp_path)
            raise

    def register(
        self,
        name: str,
        version: str = "1.0.0",
        author: str = "",
        description: str = "",
        hooks: list = None,
        permissions: list = None,
        dependencies: list = None,
    ) -> PluginManifest:
        """Register a new plugin."""
        plugin_id = f"plug_{hashlib.md5(name.lower().encode()).hexdigest()[:8]}"
        plugin = PluginManifest(
            plugin_id=plugin_id,
            name=name,
            version=version,
            author=author,
            description=description,
            hooks=hooks or [],
            permissions=permissions or [],
            dependencies=dependencies or [],
            state=PluginState.DISCOVERED,
        )
        self.plugins[plugin_id] = plugin
        self._save()
        return plugin

    def install(self, plugin_id: str) -> dict:
        """Install a plugin (mark as installed, create directory)."""
        if plugin_id not in self.plugins:
            return {"success": False, "error": f"Plugin '{plugin_id}' not found"}
        plugin = self.plugins[plugin_id]
        if plugin.state in (
            PluginState.INSTALLED,
            PluginState.ENABLED,
            PluginState.ACTIVE,
        ):
            return {"success": True, "message": "Already installed"}

        # Check dependencies
        missing = []
        for dep in plugin.dependencies:
            if dep not in self.plugins or self.plugins[dep].state not in (
                PluginState.INSTALLED,
                PluginState.ENABLED,
                PluginState.ACTIVE,
            ):
                missing.append(dep)
        if missing:
            return {"success": False, "error": f"Missing dependencies: {missing}"}

        # Create install directory
        install_dir = PLUGINS_INSTALLED / plugin_id
        install_dir.mkdir(parents=True, exist_ok=True)
        # Write manifest
        with open(install_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(plugin.to_dict(), f, indent=2)

        plugin.state = PluginState.INSTALLED
        plugin.install_path = str(install_dir)
        plugin.installed_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return {"success": True, "plugin_id": plugin_id, "path": str(install_dir)}

    def enable(self, plugin_id: str) -> dict:
        """Enable a plugin (register its hooks)."""
        if plugin_id not in self.plugins:
            return {"success": False, "error": f"Plugin '{plugin_id}' not found"}
        plugin = self.plugins[plugin_id]
        if plugin.state == PluginState.ENABLED or plugin.state == PluginState.ACTIVE:
            return {"success": True, "message": "Already enabled"}
        if plugin.state != PluginState.INSTALLED:
            return {
                "success": False,
                "error": f"Plugin state is {plugin.state.value}, must be installed first",
            }

        # Register hooks
        for hook_name in plugin.hooks:
            if hook_name not in self.hooks:
                self.hooks[hook_name] = {}
            # Store a placeholder handler (real plugins provide their own)
            self.hooks[hook_name][plugin_id] = lambda ctx, pid=plugin_id: ctx

        plugin.state = PluginState.ENABLED
        plugin.enabled_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return {
            "success": True,
            "plugin_id": plugin_id,
            "hooks_registered": plugin.hooks,
        }

    def disable(self, plugin_id: str) -> dict:
        """Disable a plugin (unregister its hooks)."""
        if plugin_id not in self.plugins:
            return {"success": False, "error": "Not found"}
        plugin = self.plugins[plugin_id]
        # Unregister hooks
        for hook_name in plugin.hooks:
            if hook_name in self.hooks and plugin_id in self.hooks[hook_name]:
                del self.hooks[hook_name][plugin_id]
        plugin.state = PluginState.DISABLED
        self._save()
        return {"success": True, "plugin_id": plugin_id}

    def uninstall(self, plugin_id: str) -> dict:
        """Uninstall a plugin completely."""
        if plugin_id not in self.plugins:
            return {"success": False, "error": "Not found"}
        self.disable(plugin_id)
        plugin = self.plugins[plugin_id]
        # Remove install directory
        if plugin.install_path and os.path.exists(plugin.install_path):
            import shutil

            shutil.rmtree(plugin.install_path, ignore_errors=True)
        del self.plugins[plugin_id]
        self._save()
        return {"success": True, "removed": plugin_id}

    def fire_hook(self, hook_point: str, context_data: dict = None) -> HookContext:
        """Fire a hook, passing context to all registered handlers."""
        ctx = HookContext(
            hook_point=hook_point, plugin_id="system", data=context_data or {}
        )
        handlers = self.hooks.get(hook_point, {})
        for plugin_id, handler in list(handlers.items()):
            try:
                ctx.plugin_id = plugin_id
                result = handler(ctx)
                if result is not None:
                    ctx.modified_data.update(result if isinstance(result, dict) else {})
            except Exception as e:
                ctx.error = str(e)
                if plugin_id in self.plugins:
                    self.plugins[plugin_id].state = PluginState.ERROR
                    self.plugins[plugin_id].error = str(e)
        return ctx

    def register_hook_handler(
        self, plugin_id: str, hook_point: str, handler: Callable
    ) -> bool:
        """Register a custom hook handler for a plugin."""
        if hook_point not in self.hooks:
            self.hooks[hook_point] = {}
        self.hooks[hook_point][plugin_id] = handler
        return True

    def list_plugins(self, state: str = None) -> list:
        plugins = list(self.plugins.values())
        if state:
            plugins = [p for p in plugins if p.state.value == state]
        return [p.to_dict() for p in plugins]

    def get_plugin(self, plugin_id: str) -> Optional[PluginManifest]:
        return self.plugins.get(plugin_id)

    def get_stats(self) -> dict:
        states = {}
        for p in self.plugins.values():
            s = p.state.value
            states[s] = states.get(s, 0) + 1
        return {
            "total_plugins": len(self.plugins),
            "by_state": states,
            "hooks_registered": sum(len(h) for h in self.hooks.values()),
            "hook_types": list(self.hooks.keys()),
        }


_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    global _manager
    if _manager is None:
        _manager = PluginManager()
        # Register built-in plugins if empty
        if not _manager.plugins:
            _manager.register_builtin_plugins()
    return _manager


# Extend PluginManager with built-in plugins
def register_builtin_plugins(self):
    """Register built-in OpenClaw v2 plugins."""
    builtins = [
        (
            "audit-trail",
            "1.0",
            "OpenClaw",
            "Log every action to audit logger",
            [HookPoint.POST_TOOL.value, HookPoint.ON_ERROR.value],
            [PluginPermission.FILE_WRITE.value],
        ),
        (
            "memory-booster",
            "1.0",
            "OpenClaw",
            "Auto-store important results in dual memory",
            [HookPoint.POST_RESPONSE.value],
            [PluginPermission.MEMORY.value],
        ),
        (
            "cost-tracker",
            "1.0",
            "OpenClaw",
            "Track API costs per session",
            [HookPoint.PRE_PROMPT.value, HookPoint.POST_RESPONSE.value],
            [PluginPermission.FILE_WRITE.value],
        ),
        (
            "guardian-watch",
            "1.0",
            "OpenClaw",
            "Constitutional checks before risky operations",
            [HookPoint.PRE_TOOL.value, HookPoint.ON_DRIFT.value],
            [PluginPermission.FILE_READ.value],
        ),
        (
            "auto-backup",
            "1.0",
            "OpenClaw",
            "Auto-backup before file edits",
            [HookPoint.PRE_TOOL.value],
            [PluginPermission.FILE_WRITE.value],
        ),
        (
            "smart-router",
            "1.0",
            "OpenClaw",
            "Route tasks to optimal model tier",
            [HookPoint.PRE_PROMPT.value],
            [PluginPermission.FILE_READ.value],
        ),
    ]
    for name, ver, author, desc, hooks, perms in builtins:
        self.register(
            name=name,
            version=ver,
            author=author,
            description=desc,
            hooks=hooks,
            permissions=perms,
        )


PluginManager.register_builtin_plugins = register_builtin_plugins


if __name__ == "__main__":
    import sys

    pm = get_plugin_manager()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        print(json.dumps(pm.get_stats(), indent=2))
    elif cmd == "list":
        for p in pm.list_plugins():
            print(f"  [{p['state']:12s}] {p['name']}: {p['description'][:50]}")
    elif cmd == "install" and len(sys.argv) > 2:
        print(json.dumps(pm.install(sys.argv[2]), indent=2))
    elif cmd == "enable" and len(sys.argv) > 2:
        print(json.dumps(pm.enable(sys.argv[2]), indent=2))
    else:
        print("Commands: stats, list, install <id>, enable <id>")
