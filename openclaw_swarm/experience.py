"""
Experience Learning - Self-improvement from past experiences
Inspired by: ChanningLua/prax-agent, faveos8758/reflexion-agent-ts
"""

import os
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import hashlib
from rich.console import Console

console = Console()


@dataclass
class Experience:
    """A learned experience"""

    id: str
    timestamp: str
    task_type: str
    context: str
    action_taken: str
    result: str
    success: bool
    lessons_learned: List[str]
    patterns: Dict[str, Any]
    confidence: float  # 0.0 to 1.0

    def __post_init__(self):
        if self.patterns is None:
            self.patterns = {}
        if self.lessons_learned is None:
            self.lessons_learned = []


@dataclass
class Lesson:
    """A specific lesson learned"""

    id: str
    timestamp: str
    task_type: str
    rule: str  # "Always do X", "Never do Y", "Prefer A over B"
    confidence: float
    evidence_count: int  # How many times this lesson was validated
    last_used: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExperienceDB:
    """
    Experience Database - Learn from past successes and failures

    Features:
    - Track successes and failures
    - Extract patterns
    - Generate rules/lessons
    - Confidence scoring
    - Pattern matching for similar tasks
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(
            storage_path
            or os.path.join(os.path.dirname(__file__), "..", "..", "data", "experience")
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.experiences_file = self.storage_path / "experiences.json"
        self.lessons_file = self.storage_path / "lessons.json"
        self.patterns_file = self.storage_path / "patterns.json"

        self.experiences: Dict[str, Experience] = {}
        self.lessons: Dict[str, Lesson] = {}
        self.patterns: Dict[str, List[str]] = {}

        self._load()

    def _load(self) -> None:
        """Load experiences from disk"""
        if self.experiences_file.exists():
            try:
                with open(self.experiences_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.experiences = {k: Experience(**v) for k, v in data.items()}
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not load experiences: {e}[/yellow]"
                )

        if self.lessons_file.exists():
            try:
                with open(self.lessons_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.lessons = {k: Lesson(**v) for k, v in data.items()}
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load lessons: {e}[/yellow]")

        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, "r", encoding="utf-8") as f:
                    self.patterns = json.load(f)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load patterns: {e}[/yellow]")

    def _save(self) -> None:
        """Save experiences to disk"""
        with open(self.experiences_file, "w", encoding="utf-8") as f:
            json.dump(
                {k: asdict(v) for k, v in self.experiences.items()},
                f,
                indent=2,
                ensure_ascii=False,
            )

        with open(self.lessons_file, "w", encoding="utf-8") as f:
            json.dump(
                {k: v.to_dict() for k, v in self.lessons.items()},
                f,
                indent=2,
                ensure_ascii=False,
            )

        with open(self.patterns_file, "w", encoding="utf-8") as f:
            json.dump(self.patterns, f, indent=2, ensure_ascii=False)

    def _generate_id(self, content: str) -> str:
        """Generate unique ID"""
        return hashlib.md5(
            f"{content}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

    def record_experience(
        self,
        task_type: str,
        context: str,
        action_taken: str,
        result: str,
        success: bool,
        patterns: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record a new experience

        Args:
            task_type: Type of task (e.g., "code_generation", "review")
            context: Input context
            action_taken: What was done
            result: Result of the action
            success: Whether it succeeded
            patterns: Extracted patterns

        Returns:
            Experience ID
        """
        exp_id = self._generate_id(f"{task_type}:{context}:{action_taken}")

        experience = Experience(
            id=exp_id,
            timestamp=datetime.now().isoformat(),
            task_type=task_type,
            context=context,
            action_taken=action_taken,
            result=result,
            success=success,
            lessons_learned=[],
            patterns=patterns or {},
            confidence=1.0 if success else 0.0,
        )

        self.experiences[exp_id] = experience

        # Extract patterns and lessons
        self._extract_lessons(experience)

        self._save()

        console.print(
            f"[green]Experience recorded: {exp_id} ({'success' if success else 'failure'})[/green]"
        )
        return exp_id

    def _extract_lessons(self, experience: Experience) -> None:
        """Extract lessons from an experience"""
        if experience.success:
            # Successful patterns become recommendations
            lesson_text = f"When doing {experience.task_type}, {experience.action_taken} works well"
            lesson_id = self._generate_id(lesson_text)

            if lesson_id in self.lessons:
                # Reinforce existing lesson
                self.lessons[lesson_id].evidence_count += 1
                self.lessons[lesson_id].confidence = min(
                    1.0, self.lessons[lesson_id].confidence + 0.1
                )
            else:
                # Create new lesson
                self.lessons[lesson_id] = Lesson(
                    id=lesson_id,
                    timestamp=datetime.now().isoformat(),
                    task_type=experience.task_type,
                    rule=f"For {experience.task_type}: {experience.action_taken}",
                    confidence=0.7,
                    evidence_count=1,
                    last_used=datetime.now().isoformat(),
                )
                experience.lessons_learned.append(lesson_id)
        else:
            # Failures become warnings
            lesson_text = (
                f"When doing {experience.task_type}, avoid {experience.action_taken}"
            )
            lesson_id = self._generate_id(lesson_text)

            if lesson_id in self.lessons:
                self.lessons[lesson_id].evidence_count += 1
            else:
                self.lessons[lesson_id] = Lesson(
                    id=lesson_id,
                    timestamp=datetime.now().isoformat(),
                    task_type=experience.task_type,
                    rule=f"For {experience.task_type}: avoid {experience.action_taken}",
                    confidence=0.5,
                    evidence_count=1,
                    last_used=datetime.now().isoformat(),
                )
                experience.lessons_learned.append(lesson_id)

    def get_lessons_for_task(self, task_type: str) -> List[Lesson]:
        """Get all lessons relevant to a task type"""
        return [
            lesson
            for lesson in self.lessons.values()
            if lesson.task_type == task_type or task_type in lesson.task_type
        ]

    def get_best_practices(self, task_type: str) -> List[str]:
        """Get best practices for a task type"""
        lessons = self.get_lessons_for_task(task_type)

        # Filter for high-confidence successful patterns
        practices = [
            lesson.rule
            for lesson in lessons
            if lesson.confidence >= 0.8 and "avoid" not in lesson.rule.lower()
        ]

        return practices

    def get_warnings(self, task_type: str) -> List[str]:
        """Get warnings for a task type"""
        lessons = self.get_lessons_for_task(task_type)

        # Filter for failure patterns
        warnings = [lesson.rule for lesson in lessons if "avoid" in lesson.rule.lower()]

        return warnings

    def get_advice(self, task_type: str) -> Dict[str, List[str]]:
        """Get advice for a task type"""
        return {
            "best_practices": self.get_best_practices(task_type),
            "warnings": self.get_warnings(task_type),
        }

    def find_similar_experiences(
        self, task_type: str, context: str, limit: int = 5
    ) -> List[Experience]:
        """Find similar past experiences"""
        # First filter by task type
        candidates = [
            exp for exp in self.experiences.values() if exp.task_type == task_type
        ]

        # Then sort by confidence and recency
        candidates.sort(key=lambda x: (x.confidence, x.timestamp), reverse=True)

        return candidates[:limit]

    def should_try_approach(
        self, task_type: str, proposed_action: str
    ) -> Tuple[bool, str]:
        """
        Determine if an approach should be tried

        Args:
            task_type: Type of task
            proposed_action: Action being considered

        Returns:
            (should_try, reason)
        """
        lessons = self.get_lessons_for_task(task_type)

        for lesson in lessons:
            if lesson.confidence >= 0.8:
                # High confidence recommendation
                if proposed_action.lower() in lesson.rule.lower():
                    if "avoid" in lesson.rule.lower():
                        return (
                            False,
                            f"Past experience suggests avoiding: {lesson.rule}",
                        )
                    else:
                        return (True, f"Past experience supports: {lesson.rule}")

        # No strong evidence either way
        return (True, "No relevant past experience found")

    def get_confidence(self, task_type: str, action: str) -> float:
        """
        Get confidence score for an action

        Returns:
            Confidence from 0.0 to 1.0
        """
        lessons = self.get_lessons_for_task(task_type)

        for lesson in lessons:
            if action.lower() in lesson.rule.lower():
                if "avoid" in lesson.rule.lower():
                    return 1.0 - lesson.confidence  # Low confidence if warned against
                else:
                    return lesson.confidence

        # No evidence
        return 0.5

    def update_after_execution(
        self, task_type: str, action: str, success: bool, context: str = ""
    ) -> None:
        """
        Update experience after task execution

        Args:
            task_type: Type of task
            action: Action taken
            success: Whether it succeeded
            context: Context string
        """
        # Record the experience
        self.record_experience(
            task_type=task_type,
            context=context,
            action_taken=action,
            result="success" if success else "failure",
            success=success,
        )

        # Find relevant lesson and update
        lesson_text = f"{action}"
        for lesson_id, lesson in self.lessons.items():
            if action.lower() in lesson.rule.lower():
                if success:
                    lesson.evidence_count += 1
                    lesson.confidence = min(1.0, lesson.confidence + 0.05)
                else:
                    lesson.confidence = max(0.0, lesson.confidence - 0.1)
                lesson.last_used = datetime.now().isoformat()
                break

        self._save()

    def get_stats(self) -> Dict[str, Any]:
        """Get experience statistics"""
        total = len(self.experiences)
        successful = sum(1 for e in self.experiences.values() if e.success)
        failed = total - successful

        lessons_count = len(self.lessons)
        high_confidence_lessons = sum(
            1 for l in self.lessons.values() if l.confidence >= 0.8
        )

        task_types = set(e.task_type for e in self.experiences.values())

        return {
            "total_experiences": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "total_lessons": lessons_count,
            "high_confidence_lessons": high_confidence_lessons,
            "task_types": list(task_types),
            "average_confidence": (
                sum(e.confidence for e in self.experiences.values()) / total
                if total > 0
                else 0
            ),
        }

    def export_rules(self, filepath: str) -> None:
        """Export learned rules to file"""
        rules = {"best_practices": {}, "warnings": {}}

        for task_type in set(l.task_type for l in self.lessons.values()):
            rules["best_practices"][task_type] = self.get_best_practices(task_type)
            rules["warnings"][task_type] = self.get_warnings(task_type)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)

        console.print(f"[green]Exported rules to {filepath}[/green]")


# Convenience functions
def learn(task_type: str, action: str, success: bool, context: str = "") -> None:
    """Quick learn from experience"""
    db = ExperienceDB()
    db.update_after_execution(task_type, action, success, context)


def get_advice(task_type: str) -> Dict[str, List[str]]:
    """Get advice for a task type"""
    db = ExperienceDB()
    return {
        "best_practices": db.get_best_practices(task_type),
        "warnings": db.get_warnings(task_type),
    }
