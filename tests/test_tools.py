"""
Tests for Tool System
"""

import pytest
import tempfile
import os
from pathlib import Path

from openclaw_swarm.tools import (
    ToolType,
    ToolResult,
    BashTool,
    ReadTool,
    WriteTool,
    EditTool,
    GrepTool,
    GlobTool,
    ToolRegistry
)


class TestToolType:
    """Test ToolType enum"""
    
    def test_tool_types_exist(self):
        """Test all tool types exist"""
        assert ToolType.BASH.value == "bash"
        assert ToolType.READ.value == "read"
        assert ToolType.WRITE.value == "write"
        assert ToolType.EDIT.value == "edit"
        assert ToolType.GREP.value == "grep"
        assert ToolType.GLOB.value == "glob"
        assert ToolType.SEARCH.value == "search"
        assert ToolType.CUSTOM.value == "custom"


class TestToolResult:
    """Test ToolResult dataclass"""
    
    def test_result_creation(self):
        """Test creating a result"""
        result = ToolResult(success=True, output="Hello")
        
        assert result.success is True
        assert result.output == "Hello"
        assert result.error is None
        assert result.exit_code == 0
    
    def test_result_with_error(self):
        """Test result with error"""
        result = ToolResult(
            success=False,
            output="",
            error="Something went wrong",
            exit_code=1
        )
        
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.exit_code == 1
    
    def test_result_with_metadata(self):
        """Test result with metadata"""
        result = ToolResult(
            success=True,
            output="",
            metadata={"path": "/tmp/test.txt", "lines": 10}
        )
        
        assert result.metadata["path"] == "/tmp/test.txt"
        assert result.metadata["lines"] == 10


class TestBashTool:
    """Test BashTool"""
    
    def test_bash_echo(self):
        """Test echo command"""
        tool = BashTool()
        result = tool.execute("echo Hello World")
        
        assert result.success is True
        assert "Hello World" in result.output
    
    def test_bash_pwd(self):
        """Test pwd command"""
        tool = BashTool()
        result = tool.execute("cd")  # Windows equivalent of pwd
        
        assert result.success is True
        assert len(result.output) > 0
    
    def test_bash_invalid_command(self):
        """Test invalid command"""
        tool = BashTool()
        result = tool.execute("invalid_command_xyz")
        
        assert result.success is False
        assert result.exit_code != 0
    
    def test_bash_with_cwd(self):
        """Test with working directory"""
        tool = BashTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = tool.execute("cd", cwd=tmpdir)  # Windows equivalent
            
            assert result.success is True
            assert tmpdir in result.output
    
    def test_bash_timeout(self):
        """Test timeout"""
        tool = BashTool(timeout=1)
        result = tool.execute("timeout /t 5", timeout=1)  # Windows equivalent of sleep
        
        assert result.success is False
        assert "timeout" in result.error.lower() or "error" in result.error.lower()


class TestReadTool:
    """Test ReadTool"""
    
    def test_read_file(self):
        """Test reading a file"""
        tool = ReadTool()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Hello World\nLine 2\nLine 3")
            f.flush()
            
            result = tool.execute(f.name)
            
            assert result.success is True
            assert "Hello World" in result.output
    
    def test_read_with_offset(self):
        """Test reading with offset"""
        tool = ReadTool()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4")
            f.flush()
            
            result = tool.execute(f.name, offset=2)
            
            assert result.success is True
            assert "Line 1" not in result.output
            assert "Line 2" in result.output
    
    def test_read_with_limit(self):
        """Test reading with limit"""
        tool = ReadTool()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4")
            f.flush()
            
            result = tool.execute(f.name, limit=2)
            
            assert result.success is True
            assert "Line 1" in result.output
            assert "Line 4" not in result.output
    
    def test_read_nonexistent_file(self):
        """Test reading nonexistent file"""
        tool = ReadTool()
        result = tool.execute("/nonexistent/file.txt")
        
        assert result.success is False
        assert "not found" in result.error.lower()


class TestWriteTool:
    """Test WriteTool"""
    
    def test_write_file(self):
        """Test writing a file"""
        tool = WriteTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            result = tool.execute(filepath, "Hello World")
            
            assert result.success is True
            assert os.path.exists(filepath)
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            assert content == "Hello World"
    
    def test_write_with_create_dirs(self):
        """Test writing with create_dirs"""
        tool = WriteTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "subdir", "test.txt")
            result = tool.execute(filepath, "Hello World", create_dirs=True)
            
            assert result.success is True
            assert os.path.exists(filepath)
    
    def test_append_mode(self):
        """Test append mode"""
        tool = WriteTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.txt")
            
            # Write initial
            tool.execute(filepath, "Line 1\n")
            
            # Append
            result = tool.execute(filepath, "Line 2\n", mode="a")
            
            assert result.success is True
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            assert "Line 1" in content
            assert "Line 2" in content


class TestEditTool:
    """Test EditTool"""
    
    def test_edit_file(self):
        """Test editing a file"""
        tool = EditTool()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Hello World")
            f.flush()
            
            result = tool.execute(f.name, "World", "Universe")
            
            assert result.success is True
            
            with open(f.name, 'r') as file:
                content = file.read()
            
            assert content == "Hello Universe"
    
    def test_edit_replace_all(self):
        """Test replacing all occurrences"""
        tool = EditTool()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("a a a a")
            f.flush()
            
            result = tool.execute(f.name, "a", "b", replace_all=True)
            
            assert result.success is True
            assert result.metadata["replacements"] == 4
    
    def test_edit_text_not_found(self):
        """Test when text not found"""
        tool = EditTool()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Hello World")
            f.flush()
            
            result = tool.execute(f.name, "xyz", "abc")
            
            assert result.success is False
            assert "not found" in result.error.lower()


class TestGrepTool:
    """Test GrepTool"""
    
    def test_grep_file(self):
        """Test searching in file"""
        tool = GrepTool()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Hello World\nLine 2\nHello Again")
            f.flush()
            
            result = tool.execute("Hello", f.name)
            
            assert result.success is True
            assert "Hello" in result.output
    
    def test_grep_regex(self):
        """Test regex search"""
        tool = GrepTool()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test123\nabc\n456test")
            f.flush()
            
            result = tool.execute(r"test\d*", f.name)
            
            assert result.success is True


class TestGlobTool:
    """Test GlobTool"""
    
    def test_glob_files(self):
        """Test finding files"""
        tool = GlobTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            Path(tmpdir, "test1.txt").touch()
            Path(tmpdir, "test2.txt").touch()
            Path(tmpdir, "other.py").touch()
            
            result = tool.execute("*.txt", path=tmpdir, recursive=False)
            
            assert result.success is True
            assert "test1.txt" in result.output
            assert "test2.txt" in result.output
            assert "other.py" not in result.output
    
    def test_glob_recursive(self):
        """Test recursive glob"""
        tool = GlobTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            subdir = Path(tmpdir, "subdir")
            subdir.mkdir()
            Path(subdir, "nested.txt").touch()
            
            result = tool.execute("*.txt", path=tmpdir, recursive=True)
            
            assert result.success is True
            assert "nested.txt" in result.output


class TestToolRegistry:
    """Test ToolRegistry"""
    
    def test_registry_initialization(self):
        """Test registry initialization"""
        registry = ToolRegistry()
        
        assert "bash" in registry.list_tools()
        assert "read" in registry.list_tools()
        assert "write" in registry.list_tools()
        assert "edit" in registry.list_tools()
        assert "grep" in registry.list_tools()
        assert "glob" in registry.list_tools()
    
    def test_get_tool(self):
        """Test getting a tool"""
        registry = ToolRegistry()
        
        bash_tool = registry.get("bash")
        
        assert bash_tool is not None
        assert bash_tool.name == "bash"
    
    def test_get_nonexistent_tool(self):
        """Test getting nonexistent tool"""
        registry = ToolRegistry()
        
        tool = registry.get("nonexistent")
        
        assert tool is None
    
    def test_execute_tool(self):
        """Test executing tool"""
        registry = ToolRegistry()
        
        result = registry.execute("bash", "echo Hello")
        
        assert result.success is True
        assert "Hello" in result.output
    
    def test_execute_nonexistent_tool(self):
        """Test executing nonexistent tool"""
        registry = ToolRegistry()
        
        result = registry.execute("nonexistent")
        
        assert result.success is False
        assert "not found" in result.error