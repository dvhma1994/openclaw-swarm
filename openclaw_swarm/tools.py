"""
OpenClaw Swarm - Tool System
Bash and file operations like OpenClaude
"""

import json
import os
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging


class ToolType(Enum):
    """Types of tools"""

    BASH = "bash"
    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    GREP = "grep"
    GLOB = "glob"
    SEARCH = "search"
    CUSTOM = "custom"


@dataclass
class ToolResult:
    """Result from a tool execution"""

    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int = 0
    duration_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Tool:
    """Base tool class"""

    def __init__(self, name: str, tool_type: ToolType, description: str = ""):
        self.name = name
        self.tool_type = tool_type
        self.description = description
        self.call_count = 0
        self.last_call_time = None

    def execute(self, *args, **kwargs) -> ToolResult:
        """Execute the tool"""
        raise NotImplementedError

    def validate(self, *args, **kwargs) -> bool:
        """Validate input"""
        return True

    def _record_call(self):
        """Record tool call"""
        self.call_count += 1
        self.last_call_time = datetime.now()


class BashTool(Tool):
    """Execute bash commands"""

    def __init__(self, timeout: int = 300):
        super().__init__(
            name="bash", tool_type=ToolType.BASH, description="Execute bash commands"
        )
        self.timeout = timeout

    def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        """
        Execute a bash command

        Args:
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            timeout: Timeout in seconds

        Returns:
            ToolResult with output/error
        """
        self._record_call()
        start_time = datetime.now()

        try:
            # Prepare environment
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)

            # Execute command (shell=False for security)
            cmd_args = shlex.split(command)
            result = subprocess.run(
                cmd_args,
                shell=False,
                capture_output=True,
                text=True,
                cwd=cwd,
                env=exec_env,
                timeout=timeout or self.timeout,
            )

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                exit_code=result.returncode,
                duration_ms=duration_ms,
            )

        except subprocess.TimeoutExpired:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout or self.timeout} seconds",
                exit_code=-1,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                exit_code=-1,
                duration_ms=duration_ms,
            )


class ReadTool(Tool):
    """Read file contents"""

    def __init__(self, max_size_mb: int = 50):
        super().__init__(
            name="read", tool_type=ToolType.READ, description="Read file contents"
        )
        self.max_size_mb = max_size_mb

    def execute(
        self,
        path: str,
        offset: int = 0,
        limit: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> ToolResult:
        """
        Read a file

        Args:
            path: File path
            offset: Line offset (1-indexed)
            limit: Max lines to read
            encoding: File encoding

        Returns:
            ToolResult with file contents
        """
        self._record_call()
        start_time = datetime.now()

        try:
            file_path = Path(path)

            # Check file exists
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File not found: {path}",
                    exit_code=1,
                )

            # Check file size
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > self.max_size_mb:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File too large: {size_mb:.2f}MB (max: {self.max_size_mb}MB)",
                    exit_code=1,
                )

            # Read file
            with open(file_path, "r", encoding=encoding) as f:
                lines = f.readlines()

            # Apply offset and limit
            if offset > 0:
                lines = lines[offset - 1 :]
            if limit:
                lines = lines[:limit]

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            return ToolResult(
                success=True,
                output="".join(lines),
                exit_code=0,
                duration_ms=duration_ms,
                metadata={
                    "path": str(file_path),
                    "total_lines": len(lines),
                    "size_mb": size_mb,
                },
            )

        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                exit_code=1,
                duration_ms=duration_ms,
            )


class WriteTool(Tool):
    """Write file contents"""

    def __init__(self):
        super().__init__(
            name="write", tool_type=ToolType.WRITE, description="Write file contents"
        )

    def execute(
        self,
        path: str,
        content: str,
        mode: str = "w",
        encoding: str = "utf-8",
        create_dirs: bool = True,
    ) -> ToolResult:
        """
        Write a file

        Args:
            path: File path
            content: Content to write
            mode: Write mode (w, a)
            encoding: File encoding
            create_dirs: Create parent directories

        Returns:
            ToolResult with status
        """
        self._record_call()
        start_time = datetime.now()

        try:
            file_path = Path(path)

            # Create parent directories
            if create_dirs and not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            size_kb = len(content.encode(encoding)) / 1024

            return ToolResult(
                success=True,
                output=f"Successfully wrote {size_kb:.2f}KB to {path}",
                exit_code=0,
                duration_ms=duration_ms,
                metadata={"path": str(file_path), "size_kb": size_kb, "mode": mode},
            )

        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                exit_code=1,
                duration_ms=duration_ms,
            )


class EditTool(Tool):
    """Edit file contents"""

    def __init__(self):
        super().__init__(
            name="edit", tool_type=ToolType.EDIT, description="Edit file contents"
        )

    def execute(
        self, path: str, old_text: str, new_text: str, replace_all: bool = False
    ) -> ToolResult:
        """
        Edit a file by replacing text

        Args:
            path: File path
            old_text: Text to find
            new_text: Text to replace with
            replace_all: Replace all occurrences

        Returns:
            ToolResult with status
        """
        self._record_call()
        start_time = datetime.now()

        try:
            file_path = Path(path)

            # Read file
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File not found: {path}",
                    exit_code=1,
                )

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Replace text
            if replace_all:
                new_content = content.replace(old_text, new_text)
                count = content.count(old_text)
            else:
                if old_text not in content:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Text not found: {old_text[:50]}...",
                        exit_code=1,
                    )
                new_content = content.replace(old_text, new_text, 1)
                count = 1

            # Write file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            return ToolResult(
                success=True,
                output=f"Successfully replaced {count} occurrence(s)",
                exit_code=0,
                duration_ms=duration_ms,
                metadata={"path": str(file_path), "replacements": count},
            )

        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                exit_code=1,
                duration_ms=duration_ms,
            )


class GrepTool(Tool):
    """Search file contents"""

    def __init__(self):
        super().__init__(
            name="grep",
            tool_type=ToolType.GREP,
            description="Search file contents with regex",
        )

    def execute(
        self,
        pattern: str,
        path: str,
        recursive: bool = True,
        file_pattern: str = "*",
        max_results: int = 100,
    ) -> ToolResult:
        """
        Search for pattern in files

        Args:
            pattern: Regex pattern
            path: Directory or file path
            recursive: Search recursively
            file_pattern: File pattern to match
            max_results: Max results to return

        Returns:
            ToolResult with matches
        """
        self._record_call()
        start_time = datetime.now()

        try:
            import re
            from pathlib import Path

            search_path = Path(path)
            regex = re.compile(pattern, re.MULTILINE)
            results = []

            # Get files to search
            if search_path.is_file():
                files = [search_path]
            elif recursive:
                files = search_path.rglob(file_pattern)
            else:
                files = search_path.glob(file_pattern)

            # Search each file
            for file_path in files:
                if not file_path.is_file():
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                results.append(
                                    {
                                        "file": str(file_path),
                                        "line": line_num,
                                        "content": line.strip(),
                                    }
                                )

                                if len(results) >= max_results:
                                    break
                except Exception:
                    logging.warning(f"Failed to read file {file_path}", exc_info=True)
                    continue

                if len(results) >= max_results:
                    break

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            return ToolResult(
                success=True,
                output=json.dumps(results, indent=2),
                exit_code=0,
                duration_ms=duration_ms,
                metadata={
                    "pattern": pattern,
                    "files_searched": (
                        len(list(files)) if hasattr(files, "__len__") else 0
                    ),
                    "matches": len(results),
                },
            )

        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                exit_code=1,
                duration_ms=duration_ms,
            )


class GlobTool(Tool):
    """Find files by pattern"""

    def __init__(self):
        super().__init__(
            name="glob", tool_type=ToolType.GLOB, description="Find files by pattern"
        )

    def execute(
        self, pattern: str, path: str = ".", recursive: bool = True
    ) -> ToolResult:
        """
        Find files matching pattern

        Args:
            pattern: Glob pattern
            path: Base path
            recursive: Search recursively

        Returns:
            ToolResult with file list
        """
        self._record_call()
        start_time = datetime.now()

        try:
            from pathlib import Path

            base_path = Path(path)

            if recursive:
                files = list(base_path.rglob(pattern))
            else:
                files = list(base_path.glob(pattern))

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            return ToolResult(
                success=True,
                output="\n".join(str(f) for f in files),
                exit_code=0,
                duration_ms=duration_ms,
                metadata={"pattern": pattern, "count": len(files)},
            )

        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                exit_code=1,
                duration_ms=duration_ms,
            )


class ToolRegistry:
    """Registry for all tools"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """Register built-in tools"""
        self.register(BashTool())
        self.register(ReadTool())
        self.register(WriteTool())
        self.register(EditTool())
        self.register(GrepTool())
        self.register(GlobTool())

    def register(self, tool: Tool):
        """Register a tool"""
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self.tools.get(name)

    def list_tools(self) -> List[str]:
        """List all tool names"""
        return list(self.tools.keys())

    def execute(self, name: str, *args, **kwargs) -> ToolResult:
        """Execute a tool by name"""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False, output="", error=f"Tool not found: {name}", exit_code=1
            )

        return tool.execute(*args, **kwargs)
