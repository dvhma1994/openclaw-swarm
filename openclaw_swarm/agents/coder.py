"""
Coder Agent - Writes and modifies code
"""

from typing import Optional
from rich.console import Console

from ..router import Router, TaskType

console = Console()


class Coder:
    """
    Coder Agent - Writes clean, efficient, well-documented code

    Uses Qwen models optimized for code generation
    """

    SYSTEM_PROMPT = """You are an expert programmer. Your job is to write clean, efficient, and well-documented code.

When writing code:
1. First, briefly explain your approach
2. Write the complete, working code
3. Include error handling
4. Add comments for complex parts
5. Follow best practices and conventions

For modifications:
1. Understand the existing code first
2. Make minimal, focused changes
3. Preserve existing functionality
4. Update comments if needed

Output format:
## Approach
[Brief explanation of your solution]

## Code
```language
[Your code here]
```

## Notes
[Any important notes about the code]

Use proper indentation and formatting. Make the code production-ready."""

    def __init__(self):
        self.router = Router()
        self.name = "Coder"
        self.model_type = TaskType.CODING

    def code(
        self,
        task: str,
        language: str = "python",
        context: Optional[str] = None,
        existing_code: Optional[str] = None,
    ) -> str:
        """
        Write code for the given task

        Args:
            task: The coding task
            language: Programming language
            context: Additional context
            existing_code: Existing code to modify (if any)

        Returns:
            Generated code as string
        """
        console.print(f"[bold green]💻 Coder working on: {language}...[/bold green]")

        prompt = self.SYSTEM_PROMPT
        prompt += f"\n\nLanguage: {language}"

        if context:
            prompt += f"\n\nContext:\n{context}"

        if existing_code:
            prompt += f"\n\nExisting code to modify:\n```\n{existing_code}\n```"

        prompt += f"\n\nTask:\n{task}"

        result = self.router.call(prompt, TaskType.CODING)

        console.print(f"[green]✓ Code generated[/green]")
        return result

    def fix(self, code: str, error: str, language: str = "python") -> str:
        """
        Fix code based on error message

        Args:
            code: The buggy code
            error: Error message or description
            language: Programming language

        Returns:
            Fixed code
        """
        console.print(f"[bold yellow]🔧 Coder fixing bug...[/bold yellow]")

        prompt = f"""{self.SYSTEM_PROMPT}

The following {language} code has an error:

```{language}
{code}
```

Error:
{error}

Please fix the code and explain what was wrong."""

        result = self.router.call(prompt, TaskType.CODING)

        console.print(f"[green]✓ Code fixed[/green]")
        return result

    def explain(self, code: str, language: str = "python") -> str:
        """
        Explain what a piece of code does

        Args:
            code: Code to explain
            language: Programming language

        Returns:
            Explanation
        """
        prompt = f"""Explain the following {language} code in simple terms:

```{language}
{code}
```

Explain:
1. What the code does overall
2. How it works step by step
3. Any important patterns or techniques used"""

        return self.router.call(prompt, TaskType.GENERAL)

    def __call__(
        self, task: str, language: str = "python", context: Optional[str] = None
    ) -> str:
        """Make Coder callable"""
        return self.code(task, language, context)
