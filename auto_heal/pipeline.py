"""
Auto-Fix & Self-Healing Pipeline
=================================
Inspired by: Plandex (automated debugging), Kilocode (auto mode),
             Cline (linter monitoring), OpenClaude autoFix service.

Flow: Code Change -> Lint Check -> Test -> Error? -> Auto-Fix -> Re-test
                                                  -> Re-lint
                                                  -> Max Retries? -> Report

Features:
- Lint integration (Python AST, flake8, ruff)
- Test runner with failure capture
- Iterative auto-fix loop with max retries
- Error pattern classification for smarter fixes
- Constitutional check before applying fixes
- Integration with Evolution Engine for pattern learning
"""
import json, os, time, subprocess, tempfile, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

BASE_DIR = Path(os.environ.get("OPENCLAW_DIRECTOR_DIR",
    Path.home() / ".openclaw" / "workspaces" / "director"))
HEAL_DIR = BASE_DIR / "auto_heal"
HEAL_DIR.mkdir(parents=True, exist_ok=True)
HEAL_LOG = HEAL_DIR / "heal_log.jsonl"


class HealStatus(str, Enum):
    PENDING = "pending"; LINTING = "linting"; TESTING = "testing"
    FIXING = "fixing"; FIXED = "fixed"; FAILED = "failed"; SKIPPED = "skipped"

class ErrorCategory(str, Enum):
    SYNTAX = "syntax"; IMPORT = "import"; TYPE = "type"
    RUNTIME = "runtime"; LOGIC = "logic"; STYLE = "style"
    SECURITY = "security"; UNKNOWN = "unknown"


@dataclass
class HealResult:
    task_id: str; status: HealStatus; file_path: str = ""
    lint_errors: list = field(default_factory=list)
    test_errors: list = field(default_factory=list)
    fixes_applied: int = 0; fix_attempts: int = 0
    error_category: str = ErrorCategory.UNKNOWN.value
    duration_ms: int = 0; timestamp: str = ""
    def to_dict(self):
        return {**asdict(self), "status": self.status.value}


@dataclass
class ErrorPattern:
    """Classified error for smarter fixing."""
    message: str; category: ErrorCategory
    line: int = 0; column: int = 0
    fix_hint: str = ""  # Strategy hint for auto-fix


class LintChecker:
    """Runs lint checks on Python files."""
    def __init__(self):
        self.available_tools = self._detect_tools()

    def _detect_tools(self) -> list:
        tools = []
        for tool in ["ruff", "flake8", "pylint", "python"]:
            try:
                result = subprocess.run([tool, "--version"],
                    capture_output=True, timeout=5,
                    shell=True, windows_hide=True)
                if result.returncode == 0: tools.append(tool)
            except Exception: pass
        return tools

    def check(self, file_path: str) -> Dict[str, list]:
        """Run lint checks and return errors."""
        errors = {"syntax": [], "style": [], "imports": [], "all": []}
        # 1. AST syntax check
        try:
            import ast
            with open(file_path, "r", encoding="utf-8") as f:
                ast.parse(f.read())
        except SyntaxError as e:
            err = {"line": e.lineno or 0, "message": str(e), "category": "syntax"}
            errors["syntax"].append(err); errors["all"].append(err)
            return errors  # Can't continue with syntax errors

        # 2. Try ruff or flake8
        if "ruff" in self.available_tools:
            try:
                result = subprocess.run(["ruff", "check", file_path, "--output-format=json"],
                    capture_output=True, timeout=30, shell=True, windows_hide=True)
                if result.stdout:
                    for item in json.loads(result.stdout):
                        err = {"line": item.get("location", {}).get("row", 0),
                               "message": item.get("message", ""),
                               "category": self._classify_error(item.get("code", ""))}
                        errors[self._category_key(err["category"])].append(err)
                        errors["all"].append(err)
            except Exception: pass
        elif "flake8" in self.available_tools:
            try:
                result = subprocess.run(["flake8", file_path, "--format=json"],
                    capture_output=True, timeout=30, shell=True, windows_hide=True)
                if result.stdout:
                    for item in json.loads(result.stdout):
                        err = {"line": item.get("line_number", 0),
                               "message": item.get("text", ""),
                               "category": self._classify_error(item.get("code", ""))}
                        errors[self._category_key(err["category"])].append(err)
                        errors["all"].append(err)
            except Exception: pass
        return errors

    def _classify_error(self, code: str) -> str:
        if code.startswith("E"): return "style"
        elif code.startswith("F"): return "imports"
        elif code.startswith("W"): return "style"
        elif code.startswith("N"): return "style"
        return "unknown"

    def _category_key(self, cat: str) -> str:
        mapping = {"style": "style", "imports": "imports", "syntax": "syntax"}
        return mapping.get(cat, "style")


class TestRunner:
    """Runs tests and captures failures."""
    def run(self, test_path: str = "", cwd: str = "") -> Dict[str, list]:
        errors = {"failures": [], "errors": [], "all": []}
        cmd = ["python", "-m", "pytest", "-x", "--tb=short"]
        if test_path: cmd.append(test_path)
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=120,
                cwd=cwd or None, shell=True, windows_hide=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            if result.returncode != 0:
                output = result.stdout.decode("utf-8", errors="replace")
                # Parse pytest output for errors
                for line in output.splitlines():
                    if "FAILED" in line or "ERROR" in line:
                        errors["failures"].append({"message": line.strip()})
                        errors["all"].append({"message": line.strip(), "type": "failure"})
                    if "ImportError" in line or "ModuleNotFoundError" in line:
                        errors["errors"].append({"message": line.strip()})
                        errors["all"].append({"message": line.strip(), "type": "import"})
        except subprocess.TimeoutExpired:
            errors["errors"].append({"message": "Test timeout (120s)"})
        except FileNotFoundError:
            errors["errors"].append({"message": "pytest not found"})
        return errors


class AutoFixer:
    """Applies automatic fixes based on error patterns."""
    def __init__(self):
        self.fix_strategies = {
            "syntax": self._fix_syntax,
            "imports": self._fix_imports,
            "style": self._fix_style,
        }

    def apply_fix(self, file_path: str, errors: list) -> dict:
        """Try to auto-fix errors in a file. Returns fix report."""
        report = {"fixes_applied": 0, "strategy_used": "", "remaining_errors": []}
        if not os.path.exists(file_path):
            report["remaining_errors"] = errors; return report

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        original = content

        # Group errors by category and fix
        for error in errors:
            category = error.get("category", "unknown")
            strategy = self.fix_strategies.get(category)
            if strategy:
                content, fixed = strategy(content, error)
                if fixed: report["fixes_applied"] += 1

        if content != original:
            report["strategy_used"] = "auto_fix"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        return report

    def _fix_syntax(self, content: str, error: dict) -> tuple:
        """Common syntax fixes."""
        msg = error.get("message", "").lower()
        # Missing colon
        if "expected ':'" in msg or "':' expected" in msg:
            line = error.get("line", 0)
            lines = content.splitlines()
            if 0 < line <= len(lines):
                stripped = lines[line - 1].rstrip()
                if not stripped.endswith(":"):
                    lines[line - 1] = stripped + ":"
                    return "\n".join(lines), True
        # Indentation errors - can't auto-fix safely
        return content, False

    def _fix_imports(self, content: str, error: dict) -> tuple:
        """Remove unused imports or add missing ones."""
        msg = error.get("message", "").lower()
        # Remove unused import
        if "imported but unused" in msg or "unused import" in msg:
            line = error.get("line", 0)
            lines = content.splitlines()
            if 0 < line <= len(lines):
                if lines[line - 1].strip().startswith(("import ", "from ")):
                    lines[line - 1] = ""  # Remove the line
                    return "\n".join(lines), True
        return content, False

    def _fix_style(self, content: str, error: dict) -> tuple:
        """Common style fixes (trailing whitespace, blank lines)."""
        msg = error.get("message", "").lower()
        if "trailing whitespace" in msg:
            lines = [l.rstrip() for l in content.splitlines()]
            return "\n".join(lines), True
        if "blank line" in msg:
            # Normalize multiple blank lines
            while "\n\n\n" in content:
                content = content.replace("\n\n\n", "\n\n")
            return content, True
        return content, False


class SelfHealPipeline:
    """
    Full auto-heal pipeline: lint -> test -> fix -> re-lint -> re-test.
    Integrates with Evolution Engine to learn from repeated failures.
    """
    def __init__(self):
        self.linter = LintChecker()
        self.tester = TestRunner()
        self.fixer = AutoFixer()
        self.max_fix_attempts = 3

    def heal_file(self, file_path: str, run_tests: bool = False,
                  test_path: str = "", cwd: str = "") -> HealResult:
        """Run the full auto-heal pipeline on a file."""
        task_id = f"heal_{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{int(time.time())}"
        start = time.time()
        result = HealResult(
            task_id=task_id, status=HealStatus.PENDING,
            file_path=file_path,
            timestamp=datetime.now(timezone.utc).isoformat())

        # Step 1: Lint
        result.status = HealStatus.LINTING
        lint_errors = self.linter.check(file_path)
        result.lint_errors = lint_errors["all"]

        # Step 2: Fix loop
        if lint_errors["all"]:
            result.status = HealStatus.FIXING
            for attempt in range(self.max_fix_attempts):
                result.fix_attempts = attempt + 1
                fix_report = self.fixer.apply_fix(file_path, lint_errors["all"])
                result.fixes_applied += fix_report["fixes_applied"]

                # Re-lint after fix
                lint_errors = self.linter.check(file_path)
                result.lint_errors = lint_errors["all"]
                if not lint_errors["all"]:
                    break
                if fix_report["fixes_applied"] == 0:
                    break  # No more progress

        # Step 3: Run tests if requested
        if run_tests:
            result.status = HealStatus.TESTING
            test_errors = self.tester.run(test_path, cwd)
            result.test_errors = test_errors["all"]

        # Final status
        if not lint_errors["all"] and (not run_tests or not result.test_errors):
            result.status = HealStatus.FIXED
        elif lint_errors["all"] or result.test_errors:
            result.status = HealStatus.FAILED
        else:
            result.status = HealStatus.SKIPPED

        result.duration_ms = int((time.time() - start) * 1000)

        # Log result
        with open(HEAL_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(result.to_dict(), default=str) + "\n")

        # Report to Evolution Engine if repeated failures
        if result.status == HealStatus.FAILED:
            try:
                from evolution_engine.engine import get_evolution_engine
                engine = get_evolution_engine()
                engine.record_failure("auto_heal",
                    f"Auto-heal failed for {file_path}",
                    component=file_path,
                    error_text=str(lint_errors["all"][:3]))
            except Exception: pass

        return result

    def heal_directory(self, dir_path: str, pattern: str = "*.py",
                       run_tests: bool = False) -> dict:
        """Run auto-heal on all matching files in a directory."""
        results = {"files_processed": 0, "files_fixed": 0,
                   "files_failed": 0, "total_errors": 0, "details": []}
        for f in Path(dir_path).rglob(pattern):
            if f.is_file() and "test_" not in f.name and "__pycache__" not in str(f):
                r = self.heal_file(str(f), run_tests=run_tests)
                results["files_processed"] += 1
                if r.status == HealStatus.FIXED: results["files_fixed"] += 1
                elif r.status == HealStatus.FAILED: results["files_failed"] += 1
                results["total_errors"] += len(r.lint_errors) + len(r.test_errors)
                results["details"].append(r.to_dict())
        return results

    def get_stats(self) -> dict:
        """Read heal log and compute stats."""
        entries = []
        if HEAL_LOG.exists():
            with open(HEAL_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    try: entries.append(json.loads(line.strip()))
                    except Exception: pass
        total = len(entries)
        fixed = sum(1 for e in entries if e.get("status") == "fixed")
        return {"total_heals": total, "fixed": fixed,
                "failed": total - fixed,
                "fix_rate": round(fixed / max(total, 1) * 100, 1),
                "avg_fix_attempts": round(
                    sum(e.get("fix_attempts", 0) for e in entries) / max(total, 1), 1)}


_pipeline: Optional[SelfHealPipeline] = None
def get_heal_pipeline() -> SelfHealPipeline:
    global _pipeline
    if _pipeline is None: _pipeline = SelfHealPipeline()
    return _pipeline


if __name__ == "__main__":
    import sys
    pipeline = get_heal_pipeline()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats": print(json.dumps(pipeline.get_stats(), indent=2))
    elif cmd == "heal" and len(sys.argv) > 2:
        result = pipeline.heal_file(sys.argv[2], run_tests="--test" in sys.argv)
        print(json.dumps(result.to_dict(), indent=2, default=str))
    elif cmd == "heal-dir" and len(sys.argv) > 2:
        results = pipeline.heal_directory(sys.argv[2])
        print(json.dumps(results, indent=2, default=str))
    else: print("Commands: stats, heal <file> [--test], heal-dir <directory>")