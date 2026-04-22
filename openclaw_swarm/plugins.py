"""
Plugin System - Easy extensions for OpenClaw Swarm
"""

import importlib.util
import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from rich.console import Console

console = Console()


class PluginType(Enum):
    """Types of plugins"""

    AGENT = "agent"  # Custom agent
    TOOL = "tool"  # Custom tool
    ROUTER = "router"  # Custom router
    MEMORY = "memory"  # Memory backend
    MIDDLEWARE = "middleware"  # Request/response middleware
    SKILL = "skill"  # Skill/plugin
    HOOK = "hook"  # Lifecycle hook


@dataclass
class PluginMetadata:
    """Plugin metadata"""

    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: str
    dependencies: List[str]
    enabled: bool = True
    priority: int = 50  # Lower = higher priority
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


@dataclass
class Plugin:
    """A loaded plugin"""

    metadata: PluginMetadata
    module_path: str
    hooks: Dict[str, Callable] = None
    config_schema: Dict[str, Any] = None

    def __post_init__(self):
        if self.hooks is None:
            self.hooks = {}
        if self.config_schema is None:
            self.config_schema = {}


class PluginManager:
    """
    Plugin Manager for OpenClaw Swarm

    Features:
    - Load plugins from directories
    - Hot-swap plugins
    - Plugin dependencies
    - Lifecycle hooks
    - Configuration management
    """

    def __init__(self, plugin_dir: Optional[str] = None):
        self.plugin_dir = Path(
            plugin_dir or os.path.join(os.path.dirname(__file__), "..", "..", "plugins")
        )
        self.plugin_dir.mkdir(parents=True, exist_ok=True)

        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[str, List[Callable]] = {}

        self._builtin_hooks = [
            "on_load",
            "on_unload",
            "before_request",
            "after_request",
            "before_agent_run",
            "after_agent_run",
            "on_error",
            "on_config_change",
        ]

        # Initialize hook lists
        for hook in self._builtin_hooks:
            self.hooks[hook] = []

    def discover_plugins(self) -> List[Dict[str, Any]]:
        """Discover available plugins"""
        discovered = []

        for plugin_path in self.plugin_dir.iterdir():
            if plugin_path.is_dir():
                metadata_file = plugin_path / "plugin.json"

                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                            metadata["path"] = str(plugin_path)
                            discovered.append(metadata)
                    except Exception as e:
                        console.print(
                            f"[yellow]Warning: Could not load {plugin_path}: {e}[/yellow]"
                        )

        return discovered

    def load_plugin(self, plugin_id: str) -> bool:
        """Load a plugin by ID"""
        # Find plugin
        plugin_path = self.plugin_dir / plugin_id

        if not plugin_path.exists():
            console.print(f"[red]Plugin not found: {plugin_id}[/red]")
            return False

        # Load metadata
        metadata_file = plugin_path / "plugin.json"

        if not metadata_file.exists():
            console.print(f"[red]Plugin metadata not found: {plugin_id}[/red]")
            return False

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata_dict = json.load(f)

            metadata = PluginMetadata(
                id=metadata_dict.get("id", plugin_id),
                name=metadata_dict.get("name", plugin_id),
                version=metadata_dict.get("version", "0.0.1"),
                description=metadata_dict.get("description", ""),
                author=metadata_dict.get("author", "Unknown"),
                plugin_type=metadata_dict.get("type", "tool"),
                dependencies=metadata_dict.get("dependencies", []),
                enabled=metadata_dict.get("enabled", True),
                priority=metadata_dict.get("priority", 50),
                config=metadata_dict.get("config", {}),
            )

            # Load main module
            main_file = plugin_path / "main.py"

            if main_file.exists():
                spec = importlib.util.spec_from_file_location(
                    f"plugin_{plugin_id}", main_file
                )

                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Extract hooks
                    hooks = {}
                    for hook_name in self._builtin_hooks:
                        if hasattr(module, hook_name):
                            hooks[hook_name] = getattr(module, hook_name)

                    plugin = Plugin(
                        metadata=metadata, module_path=str(main_file), hooks=hooks
                    )

                    self.plugins[plugin_id] = plugin

                    # Register hooks
                    for hook_name, hook_func in hooks.items():
                        self.hooks[hook_name].append(hook_func)

                    # Call on_load hook
                    if "on_load" in hooks:
                        hooks["on_load"](metadata.config)

                    console.print(
                        f"[green]Loaded plugin: {metadata.name} v{metadata.version}[/green]"
                    )
                    return True
            else:
                # Plugin without main.py - just metadata
                plugin = Plugin(
                    metadata=metadata, module_path=str(plugin_path), hooks={}
                )

                self.plugins[plugin_id] = plugin
                console.print(
                    f"[green]Loaded plugin (metadata only): {metadata.name}[/green]"
                )
                return True

        except Exception as e:
            console.print(f"[red]Error loading plugin {plugin_id}: {e}[/red]")
            return False

        return False

    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin"""
        if plugin_id not in self.plugins:
            return False

        plugin = self.plugins[plugin_id]

        # Call on_unload hook
        if "on_unload" in plugin.hooks:
            try:
                plugin.hooks["on_unload"]()
            except Exception as e:
                console.print(f"[yellow]Warning: on_unload hook failed: {e}[/yellow]")

        # Remove hooks
        for hook_name, hook_func in plugin.hooks.items():
            if hook_func in self.hooks.get(hook_name, []):
                self.hooks[hook_name].remove(hook_func)

        # Remove plugin
        del self.plugins[plugin_id]

        console.print(f"[green]Unloaded plugin: {plugin_id}[/green]")
        return True

    def reload_plugin(self, plugin_id: str) -> bool:
        """Reload a plugin"""
        if plugin_id in self.plugins:
            self.unload_plugin(plugin_id)

        return self.load_plugin(plugin_id)

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by ID"""
        return self.plugins.get(plugin_id)

    def list_plugins(self) -> List[PluginMetadata]:
        """List all loaded plugins"""
        return [p.metadata for p in self.plugins.values()]

    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin"""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].metadata.enabled = True
            return True
        return False

    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin"""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].metadata.enabled = False
            return True
        return False

    def configure_plugin(self, plugin_id: str, config: Dict[str, Any]) -> bool:
        """Configure a plugin"""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].metadata.config.update(config)

            # Call on_config_change hook
            if "on_config_change" in self.plugins[plugin_id].hooks:
                self.plugins[plugin_id].hooks["on_config_change"](config)

            return True
        return False

    def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Execute a hook on all plugins"""
        results = []

        for plugin in self.plugins.values():
            if plugin.metadata.enabled and hook_name in plugin.hooks:
                try:
                    result = plugin.hooks[hook_name](*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    console.print(
                        f"[yellow]Hook {hook_name} failed in {plugin.metadata.id}: {e}[/yellow]"
                    )

        return results

    def create_plugin_template(self, plugin_id: str, plugin_type: str = "tool") -> str:
        """Create a plugin template"""
        plugin_path = self.plugin_dir / plugin_id
        plugin_path.mkdir(parents=True, exist_ok=True)

        # Create plugin.json
        metadata = {
            "id": plugin_id,
            "name": plugin_id.replace("_", " ").title(),
            "version": "0.1.0",
            "description": "A custom plugin",
            "author": "User",
            "type": plugin_type,
            "dependencies": [],
            "enabled": True,
            "priority": 50,
            "config": {},
        }

        with open(plugin_path / "plugin.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # Create main.py
        main_content = f'''"""
{metadata["name"]} Plugin
"""

def on_load(config):
    """Called when plugin is loaded"""
    print(f"Plugin loaded with config: {{config}}")


def on_unload():
    """Called when plugin is unloaded"""
    print("Plugin unloaded")


def before_request(request):
    """Called before a request is processed"""
    return request


def after_request(response):
    """Called after a request is processed"""
    return response


def on_config_change(config):
    """Called when configuration changes"""
    print(f"Config updated: {{config}}")
'''

        with open(plugin_path / "main.py", "w", encoding="utf-8") as f:
            f.write(main_content)

        # Create README
        readme_content = f"""# {metadata["name"]}

{metadata["description"]}

## Installation

Copy this directory to your plugins folder.

## Configuration

Edit `plugin.json` to configure the plugin.

## Hooks

- `on_load`: Called when plugin is loaded
- `on_unload`: Called when plugin is unloaded
- `before_request`: Called before processing requests
- `after_request`: Called after processing requests
- `on_config_change`: Called when configuration changes
"""

        with open(plugin_path / "README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)

        console.print(f"[green]Created plugin template: {plugin_path}[/green]")

        return str(plugin_path)

    def get_stats(self) -> Dict[str, Any]:
        """Get plugin statistics"""
        return {
            "total_plugins": len(self.plugins),
            "enabled_plugins": sum(
                1 for p in self.plugins.values() if p.metadata.enabled
            ),
            "disabled_plugins": sum(
                1 for p in self.plugins.values() if not p.metadata.enabled
            ),
            "plugin_types": {
                t.value: sum(
                    1
                    for p in self.plugins.values()
                    if p.metadata.plugin_type == t.value
                )
                for t in PluginType
            },
            "hooks_registered": {
                hook: len(funcs) for hook, funcs in self.hooks.items() if funcs
            },
        }


# Convenience function
def create_plugin_manager(plugin_dir: Optional[str] = None) -> PluginManager:
    """Create a plugin manager"""
    return PluginManager(plugin_dir)
