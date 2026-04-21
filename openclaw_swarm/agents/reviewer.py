"""
Reviewer Agent - Reviews and improves code
"""

from typing import Optional
from rich.console import Console

from ..router import Router, TaskType

console = Console()


class Reviewer:
    """
    Reviewer Agent - Analyzes code for bugs, security issues, and improvements

    Uses reasoning models for thorough analysis
    """

    SYSTEM_PROMPT = """You are an expert code reviewer. Your job is to analyze code for issues and suggest improvements.

When reviewing code:
1. Check for bugs and logical errors
2. Identify security vulnerabilities
3. Look for performance issues
4. Check code style and readability
5. Suggest improvements

Be thorough but constructive. Provide specific, actionable feedback.

Output format:
## Summary
[Overall assessment]

## Issues Found
1. [Critical issue] - [Description] - [How to fix]
2. [Medium issue] - [Description] - [How to fix]
...

## Suggestions
- [Improvement suggestion]

## Code Quality Rating
[X/10] - [Why this rating]

## Improved Code (if applicable)
```language
[Improved version]
```

Focus on practical issues that matter. Don't nitpick minor style preferences."""

    def __init__(self):
        self.router = Router()
        self.name = "Reviewer"
        self.model_type = TaskType.REASONING

    def review(
        self, code: str, language: str = "python", context: Optional[str] = None
    ) -> str:
        """
        Review code and provide feedback

        Args:
            code: Code to review
            language: Programming language
            context: Additional context

        Returns:
            Review feedback
        """
        console.print(f"[bold purple]🔍 Reviewer analyzing code...[/bold purple]")

        prompt = self.SYSTEM_PROMPT
        prompt += f"\n\nLanguage: {language}"

        if context:
            prompt += f"\n\nContext:\n{context}"

        prompt += f"\n\nCode to review:\n```{language}\n{code}\n```"

        result = self.router.call(prompt, TaskType.REASONING)

        console.print(f"[green]✓ Review complete[/green]")
        return result

    def quick_check(self, code: str, language: str = "python") -> str:
        """
        Quick check for obvious issues

        Args:
            code: Code to check
            language: Programming language

        Returns:
            Quick assessment
        """
        prompt = f"""Quickly check this {language} code for obvious issues:

```{language}
{code}
```

List:
1. Critical bugs (if any)
2. Security issues (if any)
3. Major improvements needed

Be concise. Focus on what matters most."""

        return self.router.call(prompt, TaskType.REASONING)

    def security_audit(self, code: str, language: str = "python") -> str:
        """
        Security-focused review

        Args:
            code: Code to audit
            language: Programming language

        Returns:
            Security assessment
        """
        prompt = f"""Perform a security audit on this {language} code:

```{language}
{code}
```

Check for:
1. Injection vulnerabilities (SQL, command, etc.)
2. Authentication/authorization issues
3. Data exposure risks
4. Cryptographic weaknesses
5. Input validation problems

For each issue:
- Severity: Critical/High/Medium/Low
- Description
- How to fix

Be thorough. Security matters."""

        return self.router.call(prompt, TaskType.REASONING)

    def __call__(
        self, code: str, language: str = "python", context: Optional[str] = None
    ) -> str:
        """Make Reviewer callable"""
        return self.review(code, language, context)
