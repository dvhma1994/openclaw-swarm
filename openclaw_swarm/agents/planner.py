"""
Planner Agent - Plans and breaks down tasks
"""

from dataclasses import dataclass
from typing import List, Optional

from rich.console import Console

from ..router import Router, TaskType

console = Console()


@dataclass
class TaskStep:
    """A single step in the plan"""

    number: int
    description: str
    dependencies: List[int] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class Planner:
    """
    Planner Agent - Breaks down complex tasks into actionable steps

    Inspired by ai-orchestrator's planning approach
    """

    SYSTEM_PROMPT = """You are an expert task planner. Your job is to break down complex tasks into smaller, actionable steps.

When given a task:
1. Analyze the requirements
2. Identify dependencies between steps
3. Break it down into clear, numbered steps
4. Each step should be actionable and specific
5. Consider edge cases and potential issues

Output format:
## Task Analysis
[Brief analysis of what needs to be done]

## Steps
1. [First step]
2. [Second step]
...

## Considerations
[Any important notes or warnings]

Be concise but thorough. Focus on practical implementation steps."""

    def __init__(self):
        self.router = Router()
        self.name = "Planner"
        self.model_type = TaskType.REASONING

    def plan(self, task: str, context: Optional[str] = None) -> str:
        """
        Create a plan for the given task

        Args:
            task: The task to plan
            context: Additional context

        Returns:
            Planned steps as string
        """
        console.print("[bold blue]📋 Planner analyzing task...[/bold blue]")

        prompt = self.SYSTEM_PROMPT
        if context:
            prompt += f"\n\nContext:\n{context}"
        prompt += f"\n\nTask to plan:\n{task}"

        result = self.router.call(prompt, TaskType.REASONING)

        console.print("[green]✓ Plan created[/green]")
        return result

    def parse_steps(self, plan_output: str) -> List[TaskStep]:
        """
        Parse plan output into structured steps

        Args:
            plan_output: The raw plan output

        Returns:
            List of TaskStep objects
        """
        steps = []
        lines = plan_output.split("\n")

        for line in lines:
            line = line.strip()
            # Match numbered steps like "1. Do something" or "1) Do something"
            if line and (line[0].isdigit() or line.startswith("-")):
                # Extract step number and description
                parts = line.split(".", 1) if "." in line else line.split(")", 1)
                if len(parts) == 2:
                    try:
                        num = int(parts[0].strip().replace("-", "").strip())
                        desc = parts[1].strip()
                        steps.append(TaskStep(number=num, description=desc))
                    except ValueError:
                        continue

        return steps

    def __call__(self, task: str, context: Optional[str] = None) -> str:
        """Make Planner callable"""
        return self.plan(task, context)
