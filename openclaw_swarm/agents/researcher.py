"""
Researcher Agent - Searches and summarizes information
"""

from typing import Optional, List
from rich.console import Console

from ..router import Router, TaskType

console = Console()


class Researcher:
    """
    Researcher Agent - Finds and summarizes information

    Uses general-purpose models for broad knowledge
    """

    SYSTEM_PROMPT = """You are an expert researcher. Your job is to find and summarize relevant information.

When researching:
1. Identify key concepts and terms
2. Provide accurate, well-sourced information
3. Structure findings clearly
4. Note any uncertainties or limitations

Output format:
## Summary
[Concise summary of findings]

## Key Points
- [Point 1]
- [Point 2]
...

## Details
[In-depth explanation]

## References (if applicable)
- [Source or reference]

Be accurate and thorough. If you're uncertain, say so."""

    def __init__(self):
        self.router = Router()
        self.name = "Researcher"
        self.model_type = TaskType.GENERAL

    def research(
        self,
        topic: str,
        questions: Optional[List[str]] = None,
        context: Optional[str] = None,
    ) -> str:
        """
        Research a topic and provide findings

        Args:
            topic: Topic to research
            questions: Specific questions to answer
            context: Additional context

        Returns:
            Research findings
        """
        console.print(f"[bold cyan]🔎 Researcher investigating: {topic}...[/bold cyan]")

        prompt = self.SYSTEM_PROMPT

        if context:
            prompt += f"\n\nContext:\n{context}"

        prompt += f"\n\nTopic to research:\n{topic}"

        if questions:
            prompt += "\n\nPlease answer these specific questions:"
            for i, q in enumerate(questions, 1):
                prompt += f"\n{i}. {q}"

        result = self.router.call(prompt, TaskType.GENERAL)

        console.print(f"[green]✓ Research complete[/green]")
        return result

    def compare(self, items: List[str], criteria: Optional[List[str]] = None) -> str:
        """
        Compare multiple items

        Args:
            items: Items to compare
            criteria: Comparison criteria

        Returns:
            Comparison analysis
        """
        prompt = f"""Compare the following items:

Items:
{chr(10).join(f'- {item}' for item in items)}

"""

        if criteria:
            prompt += "Comparison criteria:\n"
            prompt += "\n".join(f"- {c}" for c in criteria)

        prompt += """

Provide a detailed comparison table or analysis. Highlight key differences and similarities."""

        return self.router.call(prompt, TaskType.REASONING)

    def explain(self, concept: str, level: str = "intermediate") -> str:
        """
        Explain a concept at a given level

        Args:
            concept: Concept to explain
            level: beginner, intermediate, or advanced

        Returns:
            Explanation
        """
        prompt = f"""Explain the concept of "{concept}" at a {level} level.

Be clear and use appropriate examples. Structure the explanation logically.

Include:
1. What it is (definition)
2. Why it matters
3. How it works
4. Examples
5. Related concepts"""

        return self.router.call(prompt, TaskType.GENERAL)

    def __call__(self, topic: str, questions: Optional[List[str]] = None) -> str:
        """Make Researcher callable"""
        return self.research(topic, questions)
