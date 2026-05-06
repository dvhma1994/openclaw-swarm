"""
Example: Tool System
====================

This example shows how to use tools like Bash, Read, Write, Edit, etc.
"""

import tempfile
import os
from openclaw_swarm import (
    ToolRegistry,
)


def main():
    print("=" * 60)
    print("OpenClaw Swarm - Tool System Example")
    print("=" * 60)

    # 1. Create Tool Registry
    print("\n1. Tool Registry")
    print("-" * 40)

    registry = ToolRegistry()

    print(f"Available tools: {registry.list_tools()}")

    # 2. Bash Tool
    print("\n2. Bash Tool")
    print("-" * 40)

    bash = registry.get("bash")

    # Execute command
    result = bash.execute("echo Hello World")
    print(f"Output: {result.output.strip()}")
    print(f"Success: {result.success}")

    # List files
    result = bash.execute("dir", cwd=".")
    print(f"Files in current dir: {len(result.output.splitlines())} lines")

    # 3. Read Tool
    print("\n3. Read Tool")
    print("-" * 40)

    read = registry.get("read")

    # Create a test file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        test_file = f.name

    # Read entire file
    result = read.execute(test_file)
    print(f"File content:\n{result.output}")

    # Read with offset
    result = read.execute(test_file, offset=2)
    print(f"From line 2:\n{result.output}")

    # Read with limit
    result = read.execute(test_file, limit=2)
    print(f"First 2 lines:\n{result.output}")

    # Cleanup
    os.unlink(test_file)

    # 4. Write Tool
    print("\n4. Write Tool")
    print("-" * 40)

    write = registry.get("write")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write new file
        filepath = os.path.join(tmpdir, "test.txt")
        result = write.execute(filepath, "Hello World\nLine 2\nLine 3")
        print(f"Write result: {result.output}")

        # Read back
        result = read.execute(filepath)
        print(f"Read back: {result.output[:50]}...")

        # Append to file
        result = write.execute(filepath, "\nAppended line", mode="a")
        print(f"Append result: {result.output}")

        # Read again
        result = read.execute(filepath)
        print(f"After append: {result.output}")

    # 5. Edit Tool
    print("\n5. Edit Tool")
    print("-" * 40)

    edit = registry.get("edit")

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Hello World\nThis is a test\nGoodbye World")
        edit_file = f.name

    # Replace text
    result = edit.execute(edit_file, "World", "Universe")
    print(f"Edit result: {result.output}")

    # Read edited file
    result = read.execute(edit_file)
    print(f"Edited content:\n{result.output}")

    # Cleanup
    os.unlink(edit_file)

    # 6. Grep Tool
    print("\n6. Grep Tool")
    print("-" * 40)

    grep = registry.get("grep")

    # Search in current directory
    result = grep.execute("def", ".", file_pattern="*.py", max_results=5)
    print("Found functions:")
    import json

    try:
        matches = json.loads(result.output)
        for match in matches[:5]:
            print(f"  {match['file']}:{match['line']}: {match['content'][:50]}...")
    except Exception:
        print(result.output[:200])

    # 7. Glob Tool
    print("\n7. Glob Tool")
    print("-" * 40)

    glob = registry.get("glob")

    # Find Python files
    result = glob.execute("*.py", path=".", recursive=False)
    files = result.output.split("\n")[:5]
    print("Python files (first 5):")
    for f in files:
        if f:
            print(f"  {f}")

    # 8. Direct Tool Execution via Registry
    print("\n8. Direct Tool Execution")
    print("-" * 40)

    # Execute bash command directly
    result = registry.execute("bash", "whoami")
    print(f"Current user: {result.output.strip()}")

    # Write and read in one go
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "quick.txt")
        registry.execute("write", filepath, "Quick test")
        result = registry.execute("read", filepath)
        print(f"Quick test content: {result.output.strip()}")

    # 9. Tool Statistics
    print("\n9. Tool Statistics")
    print("-" * 40)

    for tool_name in registry.list_tools():
        tool = registry.get(tool_name)
        print(f"{tool_name}: {tool.call_count} calls")

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
