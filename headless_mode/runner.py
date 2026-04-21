"""
Headless/CI Mode Runner
=======================
Inspired by: Blade Code (--headless), Kilocode (--auto), Plandex (full autonomy).

Runs the full agent loop without interactive UI, suitable for:
- CI/CD pipelines
- Automated batch tasks
- Scheduled cron jobs
- Testing in sandboxed environments

Output formats: text, json, stream-json, jsonl
Permission modes: yolo (auto-accept), plan, autoEdit
"""
import json, os, sys, time, traceback, argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field, asdict
from enum import Enum

BASE_DIR = Path(os.environ.get("OPENCLAW_DIRECTOR_DIR",
    Path.home() / ".openclaw" / "workspaces" / "director"))
HEADLESS_DIR = BASE_DIR / "headless_mode"
HEADLESS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR = HEADLESS_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class PermissionMode(str, Enum):
    YOLO = "yolo"           # Auto-accept everything
    AUTO_EDIT = "autoEdit"  # Auto-accept edits, ask for risky ops
    PLAN = "plan"           # Plan only, don't execute

class OutputFormat(str, Enum):
    TEXT = "text"; JSON = "json"; STREAM_JSON = "stream-json"; JSONL = "jsonl"


@dataclass
class HeadlessEvent:
    """An event in the headless execution stream."""
    event_type: str       # "start", "tool_call", "tool_result", "thinking", "error", "complete"
    data: dict = field(default_factory=dict)
    timestamp: str = ""
    duration_ms: int = 0

    def to_dict(self): return asdict(self)
    def to_jsonl(self): return json.dumps(self.to_dict(), default=str)


@dataclass
class HeadlessResult:
    """Final result of a headless run."""
    task: str; status: str = "pending"
    mode: str = "yolo"; format: str = "jsonl"
    events: list = field(default_factory=list)
    total_tools: int = 0; total_errors: int = 0
    total_tokens: int = 0; total_cost: float = 0.0
    started_at: str = ""; completed_at: str = ""
    duration_ms: int = 0; output_file: str = ""

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if k != "events"}


class HeadlessRunner:
    """
    Runs tasks in headless mode with full agent capabilities.
    Outputs structured event stream for CI/CD consumption.
    """
    def __init__(self, permission_mode: PermissionMode = PermissionMode.YOLO,
                 output_format: OutputFormat = OutputFormat.JSONL,
                 output_dir: Path = RESULTS_DIR):
        self.permission_mode = permission_mode
        self.output_format = output_format
        self.output_dir = output_dir
        self.events: List[HeadlessEvent] = []
        self._start_time = 0

    def _emit(self, event_type: str, data: dict = None, duration_ms: int = 0):
        event = HeadlessEvent(
            event_type=event_type, data=data or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=duration_ms)
        self.events.append(event)
        # Stream output
        if self.output_format == OutputFormat.JSONL:
            print(event.to_jsonl(), flush=True)
        elif self.output_format == OutputFormat.STREAM_JSON:
            print(json.dumps(event.to_dict(), default=str), flush=True)
        elif self.output_format == OutputFormat.JSON:
            pass  # Collect, output at end
        elif self.output_format == OutputFormat.TEXT:
            if event_type == "tool_call":
                print(f"  > {data.get('tool', '?')}: {str(data.get('input', ''))[:80]}", flush=True)
            elif event_type == "tool_result":
                status = "OK" if not data.get("error") else "FAIL"
                print(f"  < {status}: {str(data.get('output', ''))[:80]}", flush=True)
            elif event_type == "error":
                print(f"  ! ERROR: {data.get('message', '')}", flush=True)
            elif event_type == "complete":
                print(f"  DONE: {data.get('status', '')}", flush=True)

    def run_task(self, task: str, executor_fn=None) -> HeadlessResult:
        """
        Run a task in headless mode.
        executor_fn: Optional callable(task: str, runner: HeadlessRunner) -> str
        If no executor_fn provided, delegates to the Director workflow.
        """
        result = HeadlessResult(
            task=task, mode=self.permission_mode.value,
            format=self.output_format.value,
            started_at=datetime.now(timezone.utc).isoformat())
        self._start_time = time.time()
        self.events = []

        self._emit("start", {"task": task, "mode": self.permission_mode.value})

        try:
            # Step 1: Constitutional pre-check
            self._emit("tool_call", {"tool": "constitutional_pre_check",
                        "input": {"action": "execute_task", "params": {"task": task[:200]}}})
            check_allowed = self._constitutional_check(task)
            self._emit("tool_result", {"tool": "constitutional_pre_check",
                        "output": {"allowed": check_allowed}})

            if not check_allowed:
                self._emit("error", {"message": "Task blocked by constitutional AI"})
                result.status = "blocked"
                self._finalize(result)
                return result

            # Step 2: Route to model
            self._emit("tool_call", {"tool": "cost_router",
                        "input": {"task": task[:100]}})
            tier = self._route_task(task)
            self._emit("tool_result", {"tool": "cost_router",
                        "output": {"tier": tier}})

            # Step 3: Execute
            if executor_fn:
                output = executor_fn(task, self)
            else:
                output = self._default_executor(task, tier)

            # Step 4: Auto-heal if code was generated
            if output and self.permission_mode == PermissionMode.YOLO:
                self._emit("tool_call", {"tool": "auto_heal",
                            "input": {"content_length": len(str(output))}})

            result.status = "completed"
            self._emit("complete", {"status": "completed", "output_length": len(str(output))})

        except Exception as e:
            result.status = "error"
            result.total_errors += 1
            self._emit("error", {"message": str(e), "traceback": traceback.format_exc()[:500]})

        self._finalize(result)
        return result

    def _constitutional_check(self, task: str) -> bool:
        """Run constitutional pre-check."""
        try:
            from constitutional_ai import get_checker
            checker = get_checker()
            result = checker.pre_check("execute_code",
                                       {"action_type": "execute_code",
                                        "source": "headless",
                                        "code": task[:200]})
            return result.allowed
        except Exception:
            return True  # Allow if constitutional AI not available

    def _route_task(self, task: str) -> str:
        """Route task to appropriate model tier."""
        try:
            from skill_contract import SkillRegistry, register_core_skills
            registry = SkillRegistry()
            register_core_skills(registry)
            valid, msg = registry.validate_execution("cost_router",
                {"task_description": task})
            return "sonnet"  # Default
        except Exception:
            return "sonnet"

    def _default_executor(self, task: str, tier: str) -> str:
        """Default executor: records the task and returns a structured response."""
        self._emit("tool_call", {"tool": "director", "input": {"task": task[:200], "tier": tier}})
        # In production, this would call the actual LLM
        output = f"Task queued: {task[:100]} (tier: {tier})"
        self._emit("tool_result", {"tool": "director", "output": output})
        return output

    def _finalize(self, result: HeadlessResult):
        """Finalize result and save to file."""
        result.duration_ms = int((time.time() - self._start_time) * 1000)
        result.completed_at = datetime.now(timezone.utc).isoformat()
        result.events = [e.to_dict() for e in self.events]
        result.total_tools = len([e for e in self.events if e.event_type == "tool_call"])
        result.total_errors = len([e for e in self.events if e.event_type == "error"])

        # Save result
        result_file = self.output_dir / f"result_{int(time.time())}.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        result.output_file = str(result_file)

        # Final JSON output if json format
        if self.output_format == OutputFormat.JSON:
            print(json.dumps(result.to_dict(), indent=2, default=str))

    def run_batch(self, tasks: List[str], executor_fn=None) -> List[HeadlessResult]:
        """Run multiple tasks sequentially."""
        results = []
        for task in tasks:
            result = self.run_task(task, executor_fn)
            results.append(result)
        return results

    @staticmethod
    def from_args(args: list = None) -> "HeadlessRunner":
        """Create a runner from CLI arguments."""
        parser = argparse.ArgumentParser(description="OpenClaw Headless Runner")
        parser.add_argument("task", nargs="?", help="Task to run")
        parser.add_argument("--permission-mode", "-p", default="yolo",
            choices=["yolo", "autoEdit", "plan"], help="Permission mode")
        parser.add_argument("--output-format", "-f", default="jsonl",
            choices=["text", "json", "stream-json", "jsonl"], help="Output format")
        parser.add_argument("--input-file", "-i", help="File with tasks (one per line)")
        parsed = parser.parse_args(args)

        return HeadlessRunner(
            permission_mode=PermissionMode(parsed.permission_mode),
            output_format=OutputFormat(parsed.output_format))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python runner.py <task> [--permission-mode yolo|autoEdit|plan] [--output-format text|json|jsonl]")
        print("       python runner.py --input-file tasks.txt")
        sys.exit(1)

    runner = HeadlessRunner.from_args()
    task = sys.argv[1] if sys.argv[1] not in ("--permission-mode", "--output-format", "--input-file") else None
    if task:
        result = runner.run_task(task)
    elif "--input-file" in sys.argv:
        idx = sys.argv.index("--input-file")
        filepath = sys.argv[idx + 1]
        with open(filepath, "r") as f:
            tasks = [l.strip() for l in f if l.strip()]
        results = runner.run_batch(tasks)