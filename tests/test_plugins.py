"""
Tests for Plugin System
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path

from openclaw_swarm.plugins import (
    PluginManager,
    PluginType,
    PluginMetadata,
    create_plugin_manager
)


class TestPluginManager:
    """Test Plugin Manager"""
    
    @pytest.fixture
    def temp_plugin_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_plugin_manager_init(self, temp_plugin_dir):
        """Test initialization"""
        pm = PluginManager(temp_plugin_dir)
        assert pm.plugin_dir == Path(temp_plugin_dir)
        assert len(pm.plugins) == 0
    
    def test_discover_plugins_empty(self, temp_plugin_dir):
        """Test discovering plugins in empty directory"""
        pm = PluginManager(temp_plugin_dir)
        discovered = pm.discover_plugins()
        assert len(discovered) == 0
    
    def test_create_plugin_template(self, temp_plugin_dir):
        """Test creating plugin template"""
        pm = PluginManager(temp_plugin_dir)
        
        plugin_path = pm.create_plugin_template("test_plugin", "tool")
        
        assert Path(plugin_path).exists()
        assert (Path(plugin_path) / "plugin.json").exists()
        assert (Path(plugin_path) / "main.py").exists()
        assert (Path(plugin_path) / "README.md").exists()
    
    def test_load_plugin(self, temp_plugin_dir):
        """Test loading a plugin"""
        pm = PluginManager(temp_plugin_dir)
        
        # Create template
        pm.create_plugin_template("test_plugin")
        
        # Load it
        result = pm.load_plugin("test_plugin")
        
        assert result is True
        assert "test_plugin" in pm.plugins
    
    def test_unload_plugin(self, temp_plugin_dir):
        """Test unloading a plugin"""
        pm = PluginManager(temp_plugin_dir)
        
        pm.create_plugin_template("test_plugin")
        pm.load_plugin("test_plugin")
        
        result = pm.unload_plugin("test_plugin")
        
        assert result is True
        assert "test_plugin" not in pm.plugins
    
    def test_reload_plugin(self, temp_plugin_dir):
        """Test reloading a plugin"""
        pm = PluginManager(temp_plugin_dir)
        
        pm.create_plugin_template("test_plugin")
        pm.load_plugin("test_plugin")
        
        # Modify metadata
        pm.plugins["test_plugin"].metadata.name = "Modified"
        
        # Reload
        result = pm.reload_plugin("test_plugin")
        
        assert result is True
        # Name should be reset to original from file
        assert pm.plugins["test_plugin"].metadata.name == "Test Plugin"
    
    def test_enable_disable_plugin(self, temp_plugin_dir):
        """Test enabling and disabling plugins"""
        pm = PluginManager(temp_plugin_dir)
        
        pm.create_plugin_template("test_plugin")
        pm.load_plugin("test_plugin")
        
        # Disable
        result = pm.disable_plugin("test_plugin")
        assert result is True
        assert pm.plugins["test_plugin"].metadata.enabled is False
        
        # Enable
        result = pm.enable_plugin("test_plugin")
        assert result is True
        assert pm.plugins["test_plugin"].metadata.enabled is True
    
    def test_configure_plugin(self, temp_plugin_dir):
        """Test configuring a plugin"""
        pm = PluginManager(temp_plugin_dir)
        
        pm.create_plugin_template("test_plugin")
        pm.load_plugin("test_plugin")
        
        config = {"setting1": "value1", "setting2": 42}
        result = pm.configure_plugin("test_plugin", config)
        
        assert result is True
        assert pm.plugins["test_plugin"].metadata.config["setting1"] == "value1"
        assert pm.plugins["test_plugin"].metadata.config["setting2"] == 42
    
    def test_list_plugins(self, temp_plugin_dir):
        """Test listing plugins"""
        pm = PluginManager(temp_plugin_dir)
        
        pm.create_plugin_template("plugin1")
        pm.create_plugin_template("plugin2")
        pm.load_plugin("plugin1")
        pm.load_plugin("plugin2")
        
        plugins = pm.list_plugins()
        
        assert len(plugins) == 2
        assert any(p.id == "plugin1" for p in plugins)
        assert any(p.id == "plugin2" for p in plugins)
    
    def test_get_plugin(self, temp_plugin_dir):
        """Test getting a specific plugin"""
        pm = PluginManager(temp_plugin_dir)
        
        pm.create_plugin_template("test_plugin")
        pm.load_plugin("test_plugin")
        
        plugin = pm.get_plugin("test_plugin")
        
        assert plugin is not None
        assert plugin.metadata.id == "test_plugin"
    
    def test_get_stats(self, temp_plugin_dir):
        """Test getting statistics"""
        pm = PluginManager(temp_plugin_dir)
        
        pm.create_plugin_template("test_plugin")
        pm.load_plugin("test_plugin")
        
        stats = pm.get_stats()
        
        assert "total_plugins" in stats
        assert stats["total_plugins"] == 1
        assert "enabled_plugins" in stats
        assert "hooks_registered" in stats
    
    def test_discover_plugins(self, temp_plugin_dir):
        """Test discovering existing plugins"""
        pm = PluginManager(temp_plugin_dir)
        
        # Create multiple plugins
        pm.create_plugin_template("plugin1")
        pm.create_plugin_template("plugin2")
        
        discovered = pm.discover_plugins()
        
        assert len(discovered) == 2
        assert any(p["id"] == "plugin1" for p in discovered)
        assert any(p["id"] == "plugin2" for p in discovered)


class TestPluginMetadata:
    """Test Plugin Metadata"""
    
    def test_metadata_creation(self):
        """Test creating plugin metadata"""
        metadata = PluginMetadata(
            id="test",
            name="Test Plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
            plugin_type="tool",
            dependencies=[]
        )
        
        assert metadata.id == "test"
        assert metadata.name == "Test Plugin"
        assert metadata.version == "1.0.0"
        assert metadata.enabled is True
        assert metadata.priority == 50
    
    def test_metadata_with_config(self):
        """Test metadata with configuration"""
        metadata = PluginMetadata(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test",
            author="Author",
            plugin_type="tool",
            dependencies=[],
            config={"key": "value"}
        )
        
        assert metadata.config == {"key": "value"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])