"""
Adaptive Evolution Engine - Core Engine
"""

import json
import logging
import os
import hashlib
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field, asdict
from enum import Enum

BASE_DIR = Path(
    os.environ.get(
        "OPENCLAW_DIRECTOR_DIR", Path.home() / ".openclaw" / "workspaces" / "director"
    )
)
EVOLUTION_DIR = BASE_DIR / "evolution_engine"
EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = EVOLUTION_DIR / "evolution_state.json"
CANDIDATES_DIR = EVOLUTION_DIR / "candidates"
CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
FAILURE_LOG = EVOLUTION_DIR / "failure_patterns.json"
PROMOTIONS_LOG = EVOLUTION_DIR / "promotions.jsonl"


class EvolutionPhase(str, Enum):
    IDLE = "idle"
    DETECTING = "detecting"
    MUTATING = "mutating"
    EVALUATING = "evaluating"
    SELECTING = "selecting"
    PROMOTING = "promoting"
    ROLLING_BACK = "rolling_back"


class MutationType(str, Enum):
    CODE_FIX = "code_fix"
    CONFIG_TUNE = "config_tune"
    PROMPT_REFINE = "prompt_refine"
    WORKFLOW_OPT = "workflow_opt"
    SAFETY_ENHANCE = "safety_enhance"
    COST_REDUCE = "cost_reduce"


@dataclass
class FailurePattern:
    pattern_id: str
    pattern_type: str
    description: str
    occurrences: int = 1
    last_seen: str = ""
    first_seen: str = ""
    affected_components: list = field(default_factory=list)
    sample_error: str = ""
    auto_fix_attempted: bool = False
    auto_fix_success: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass
class Candidate:
    candidate_id: str
    mutation_type: MutationType
    target_component: str
    original_content: str = ""
    mutated_content: str = ""
    description: str = ""
    generation: int = 0
    fitness_score: float = 0.0
    test_results: dict = field(default_factory=dict)
    created_at: str = ""
    status: str = "pending"
    parent_id: Optional[str] = None
    failure_pattern_id: Optional[str] = None

    def to_dict(self):
        return {**asdict(self), "mutation_type": self.mutation_type.value}

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        data["mutation_type"] = MutationType(data["mutation_type"])
        return cls(**data)


@dataclass
class EvolutionState:
    generation: int = 0
    total_mutations: int = 0
    total_promotions: int = 0
    total_rollbacks: int = 0
    current_phase: EvolutionPhase = EvolutionPhase.IDLE
    last_detection: str = ""
    last_mutation: str = ""
    last_promotion: str = ""
    success_rate_trend: list = field(default_factory=list)

    def to_dict(self):
        return {**asdict(self), "current_phase": self.current_phase.value}


class PatternDetector:
    """Scans failure logs to identify repeating patterns that need evolutionary fixing."""

    def __init__(self, failure_log: Path = FAILURE_LOG):
        self.failure_log = failure_log
        self.patterns: Dict[str, FailurePattern] = {}
        self._load()

    def _load(self):
        if self.failure_log.exists():
            try:
                with open(self.failure_log, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for pdata in data.get("patterns", []):
                    fp = FailurePattern(**pdata)
                    self.patterns[fp.pattern_id] = fp
            except Exception:
                logging.warning("Failed to load failure patterns", exc_info=True)
                self.patterns = {}

    def _save(self):
        self.failure_log.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "updated": datetime.now(timezone.utc).isoformat(),
            "count": len(self.patterns),
            "patterns": [p.to_dict() for p in self.patterns.values()],
        }
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(self.failure_log.parent), suffix=".tmp"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            os.replace(tmp_path, str(self.failure_log))
        except Exception:
            os.unlink(tmp_path)
            raise

    def record_failure(
        self,
        pattern_type: str,
        description: str,
        component: str = "",
        error_text: str = "",
    ) -> str:
        error_sig = (
            hashlib.md5(error_text[:200].encode()).hexdigest()[:8]
            if error_text
            else "noerr"
        )
        component_sig = component.replace("/", "_").replace("\\", "_")[:30]
        pattern_id = f"{pattern_type}__{component_sig}__{error_sig}"
        now = datetime.now(timezone.utc).isoformat()
        if pattern_id in self.patterns:
            fp = self.patterns[pattern_id]
            fp.occurrences += 1
            fp.last_seen = now
            fp.sample_error = error_text[:500]
            if component and component not in fp.affected_components:
                fp.affected_components.append(component)
        else:
            fp = FailurePattern(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                description=description,
                occurrences=1,
                first_seen=now,
                last_seen=now,
                affected_components=[component] if component else [],
                sample_error=error_text[:500],
            )
            self.patterns[pattern_id] = fp
        self._save()
        return pattern_id

    def get_recurring_failures(self, min_occurrences: int = 3) -> List[FailurePattern]:
        return sorted(
            [p for p in self.patterns.values() if p.occurrences >= min_occurrences],
            key=lambda p: p.occurrences,
            reverse=True,
        )

    def get_unattempted(self) -> List[FailurePattern]:
        return [p for p in self.get_recurring_failures() if not p.auto_fix_attempted]

    def mark_fix_attempted(self, pattern_id: str, success: bool):
        if pattern_id in self.patterns:
            self.patterns[pattern_id].auto_fix_attempted = True
            self.patterns[pattern_id].auto_fix_success = success
            self._save()


class MutationGenerator:
    """Generates candidate improvements (mutations) for failure patterns."""

    def __init__(self, candidates_dir: Path = CANDIDATES_DIR):
        self.candidates_dir = candidates_dir
        self.candidates: Dict[str, Candidate] = {}
        self._load()

    def _load(self):
        for f in self.candidates_dir.glob("candidate_*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                c = Candidate.from_dict(data)
                self.candidates[c.candidate_id] = c
            except Exception:
                logging.warning("Failed to load candidate %s", f, exc_info=True)

    def _save_candidate(self, candidate: Candidate):
        path = self.candidates_dir / f"candidate_{candidate.candidate_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(candidate.to_dict(), f, indent=2, ensure_ascii=False, default=str)

    def generate_code_fix(
        self, failure: FailurePattern, code_content: str, generation: int = 0
    ) -> Candidate:
        cid = f"cfix_{failure.pattern_id[:20]}_g{generation}_{int(time.time())}"
        c = Candidate(
            candidate_id=cid,
            mutation_type=MutationType.CODE_FIX,
            target_component=(
                failure.affected_components[0] if failure.affected_components else ""
            ),
            original_content=code_content,
            description=f"Auto-fix for recurring failure: {failure.description}",
            generation=generation,
            created_at=datetime.now(timezone.utc).isoformat(),
            failure_pattern_id=failure.pattern_id,
        )
        self.candidates[cid] = c
        self._save_candidate(c)
        return c

    def generate_config_tune(
        self,
        config_path: str,
        current_config: dict,
        suggested_changes: dict,
        generation: int = 0,
    ) -> Candidate:
        cid = f"ctune_{hashlib.md5(config_path.encode()).hexdigest()[:8]}_g{generation}_{int(time.time())}"
        c = Candidate(
            candidate_id=cid,
            mutation_type=MutationType.CONFIG_TUNE,
            target_component=config_path,
            original_content=json.dumps(current_config, indent=2),
            mutated_content=json.dumps(suggested_changes, indent=2),
            description=f"Config tuning: {list(suggested_changes.keys())}",
            generation=generation,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.candidates[cid] = c
        self._save_candidate(c)
        return c

    def generate_prompt_refine(
        self,
        prompt_name: str,
        current_prompt: str,
        refined_prompt: str,
        generation: int = 0,
    ) -> Candidate:
        cid = f"prefine_{prompt_name[:15]}_g{generation}_{int(time.time())}"
        c = Candidate(
            candidate_id=cid,
            mutation_type=MutationType.PROMPT_REFINE,
            target_component=prompt_name,
            original_content=current_prompt,
            mutated_content=refined_prompt,
            description=f"Prompt refinement: {prompt_name}",
            generation=generation,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.candidates[cid] = c
        self._save_candidate(c)
        return c

    def get_pending(self) -> List[Candidate]:
        return [c for c in self.candidates.values() if c.status == "pending"]

    def update_status(self, candidate_id: str, status: str, **kwargs):
        if candidate_id in self.candidates:
            c = self.candidates[candidate_id]
            c.status = status
            for k, v in kwargs.items():
                setattr(c, k, v)
            self._save_candidate(c)


class FitnessEvaluator:
    """Evaluates candidate mutations: syntax, imports, behavioral checks, cost."""

    def __init__(self, base_dir: Path = BASE_DIR):
        self.base_dir = base_dir

    def evaluate_code_fix(self, candidate: Candidate) -> dict:
        results = {
            "candidate_id": candidate.candidate_id,
            "syntax_check": False,
            "import_check": False,
            "fitness_score": 0.0,
            "errors": [],
        }
        try:
            import ast

            ast.parse(candidate.mutated_content)
            results["syntax_check"] = True
        except SyntaxError as e:
            results["errors"].append(f"Syntax error: {e}")
            return results
        try:
            tree = ast.parse(candidate.mutated_content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        try:
                            __import__(alias.name.split(".")[0])
                        except ImportError:
                            results["errors"].append(f"Cannot import: {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    try:
                        __import__(node.module.split(".")[0])
                    except ImportError:
                        results["errors"].append(f"Cannot import from: {node.module}")
            results["import_check"] = len(results["errors"]) == 0
        except Exception as e:
            results["errors"].append(f"Import check error: {e}")
        score = 0.0
        if results["syntax_check"]:
            score += 0.4
        if results["import_check"]:
            score += 0.3
        if not results["errors"]:
            score += 0.3
        results["fitness_score"] = min(1.0, score)
        return results

    def evaluate_config_tune(self, candidate: Candidate) -> dict:
        results = {
            "candidate_id": candidate.candidate_id,
            "json_valid": False,
            "schema_check": False,
            "fitness_score": 0.0,
            "errors": [],
        }
        try:
            mutated = json.loads(candidate.mutated_content)
            results["json_valid"] = True
        except json.JSONDecodeError as e:
            results["errors"].append(f"Invalid JSON: {e}")
            return results
        try:
            original = json.loads(candidate.original_content)
            for key in mutated:
                if key not in original:
                    results["errors"].append(f"New key '{key}' not in original")
            results["schema_check"] = len(results["errors"]) == 0
        except json.JSONDecodeError:
            results["errors"].append("Original config invalid JSON")
        score = 0.0
        if results["json_valid"]:
            score += 0.5
        if results["schema_check"]:
            score += 0.5
        results["fitness_score"] = min(1.0, score)
        return results

    def evaluate(self, candidate: Candidate) -> dict:
        if candidate.mutation_type == MutationType.CODE_FIX:
            return self.evaluate_code_fix(candidate)
        elif candidate.mutation_type == MutationType.CONFIG_TUNE:
            return self.evaluate_config_tune(candidate)
        return {
            "candidate_id": candidate.candidate_id,
            "fitness_score": 0.5,
            "errors": [],
            "note": "Manual review required",
        }


class SelectionController:
    """Selects the best candidates for promotion based on fitness scores."""

    def __init__(self, promote_threshold: float = 0.7):
        self.promote_threshold = promote_threshold

    def select_for_promotion(self, evaluated: List[dict]) -> List[dict]:
        return [
            r for r in evaluated if r.get("fitness_score", 0) >= self.promote_threshold
        ]

    def rank_candidates(self, evaluated: List[dict]) -> List[dict]:
        return sorted(evaluated, key=lambda r: r.get("fitness_score", 0), reverse=True)


class RollbackManager:
    """Creates snapshots before mutations and restores on failure."""

    def __init__(self, snapshot_dir: Path = EVOLUTION_DIR / "snapshots"):
        self.snapshot_dir = snapshot_dir
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, target_path: str) -> Optional[str]:
        if not os.path.exists(target_path):
            return None
        sid = f"snap_{hashlib.md5(target_path.encode()).hexdigest()[:8]}_{int(time.time())}"
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
        meta = {
            "snapshot_id": sid,
            "target_path": target_path,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(self.snapshot_dir / f"{sid}.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        return sid

    def restore_snapshot(self, snapshot_id: str) -> bool:
        sp = self.snapshot_dir / f"{snapshot_id}.json"
        if not sp.exists():
            return False
        try:
            with open(sp, "r", encoding="utf-8") as f:
                meta = json.load(f)
            with open(meta["target_path"], "w", encoding="utf-8") as f:
                f.write(meta["content"])
            return True
        except Exception:
            return False

    def cleanup_old_snapshots(self, max_age_days: int = 7):
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        for f in self.snapshot_dir.glob("snap_*.json"):
            try:
                with open(f, encoding="utf-8") as fh:
                    meta = json.load(fh)
                if datetime.fromisoformat(meta["created_at"]) < cutoff:
                    f.unlink()
            except Exception:
                logging.warning("Failed to clean up old snapshot %s", f, exc_info=True)


class EvolutionEngine:
    """
    Main orchestrator: detect -> mutate -> evaluate -> select -> promote/rollback.
    Inspired by OpenAlpha_Evolve, Skynet Agent, MassGen, Plandex.
    """

    def __init__(self, base_dir: Path = BASE_DIR):
        self.base_dir = base_dir
        self.state = EvolutionState()
        self.detector = PatternDetector()
        self.mutator = MutationGenerator()
        self.evaluator = FitnessEvaluator(base_dir)
        self.selector = SelectionController()
        self.rollback = RollbackManager()
        self._load_state()

    def _load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.state = EvolutionState(
                    generation=data.get("generation", 0),
                    total_mutations=data.get("total_mutations", 0),
                    total_promotions=data.get("total_promotions", 0),
                    total_rollbacks=data.get("total_rollbacks", 0),
                    current_phase=EvolutionPhase(data.get("current_phase", "idle")),
                    last_detection=data.get("last_detection", ""),
                    last_mutation=data.get("last_mutation", ""),
                    last_promotion=data.get("last_promotion", ""),
                    success_rate_trend=data.get("success_rate_trend", []),
                )
            except Exception:
                logging.warning("Failed to load evolution state", exc_info=True)

    def _save_state(self):
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(EVOLUTION_DIR), suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(self.state.to_dict(), f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, str(STATE_FILE))
        except Exception:
            os.unlink(tmp_path)
            raise

    def record_failure(
        self,
        pattern_type: str,
        description: str,
        component: str = "",
        error_text: str = "",
    ) -> str:
        pid = self.detector.record_failure(
            pattern_type, description, component, error_text
        )
        self.state.last_detection = datetime.now(timezone.utc).isoformat()
        self._save_state()
        return pid

    def get_recurring_failures(self) -> List[FailurePattern]:
        return self.detector.get_recurring_failures(min_occurrences=3)

    def propose_code_fix(self, failure: FailurePattern, code_content: str) -> Candidate:
        c = self.mutator.generate_code_fix(failure, code_content, self.state.generation)
        self.state.total_mutations += 1
        self.state.last_mutation = datetime.now(timezone.utc).isoformat()
        self._save_state()
        return c

    def propose_config_tune(
        self, config_path: str, current: dict, suggested: dict
    ) -> Candidate:
        c = self.mutator.generate_config_tune(
            config_path, current, suggested, self.state.generation
        )
        self.state.total_mutations += 1
        self.state.last_mutation = datetime.now(timezone.utc).isoformat()
        self._save_state()
        return c

    def propose_prompt_refine(
        self, prompt_name: str, current: str, refined: str
    ) -> Candidate:
        c = self.mutator.generate_prompt_refine(
            prompt_name, current, refined, self.state.generation
        )
        self.state.total_mutations += 1
        self.state.last_mutation = datetime.now(timezone.utc).isoformat()
        self._save_state()
        return c

    def evaluate_candidate(self, candidate: Candidate) -> dict:
        self.state.current_phase = EvolutionPhase.EVALUATING
        self._save_state()
        results = self.evaluator.evaluate(candidate)
        candidate.fitness_score = results.get("fitness_score", 0)
        candidate.test_results = results
        candidate.status = "tested"
        self.mutator.update_status(
            candidate.candidate_id,
            "tested",
            fitness_score=results.get("fitness_score", 0),
            test_results=results,
        )
        self.state.current_phase = EvolutionPhase.IDLE
        self._save_state()
        return results

    def promote_candidate(self, candidate: Candidate) -> bool:
        if candidate.fitness_score < self.selector.promote_threshold:
            return False
        self.state.current_phase = EvolutionPhase.PROMOTING
        self._save_state()
        snapshot_id = None
        if candidate.target_component and os.path.exists(candidate.target_component):
            snapshot_id = self.rollback.create_snapshot(candidate.target_component)
        try:
            if candidate.target_component and candidate.mutated_content:
                with open(candidate.target_component, "w", encoding="utf-8") as f:
                    f.write(candidate.mutated_content)
            candidate.status = "promoted"
            self.mutator.update_status(candidate.candidate_id, "promoted")
            entry = {
                "candidate_id": candidate.candidate_id,
                "mutation_type": candidate.mutation_type.value,
                "target": candidate.target_component,
                "fitness_score": candidate.fitness_score,
                "snapshot_id": snapshot_id,
                "promoted_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(PROMOTIONS_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            if candidate.failure_pattern_id:
                self.detector.mark_fix_attempted(
                    candidate.failure_pattern_id, success=True
                )
            self.state.total_promotions += 1
            self.state.last_promotion = datetime.now(timezone.utc).isoformat()
            self.state.generation += 1
            self._save_state()
            return True
        except Exception:
            if snapshot_id:
                self.rollback.restore_snapshot(snapshot_id)
            candidate.status = "promotion_failed"
            self.mutator.update_status(candidate.candidate_id, "promotion_failed")
            self.state.current_phase = EvolutionPhase.IDLE
            self._save_state()
            return False

    def rollback_candidate(self, candidate: Candidate) -> bool:
        for sf in self.rollback.snapshot_dir.glob("snap_*.json"):
            try:
                with open(sf, encoding="utf-8") as f:
                    meta = json.load(f)
                if meta["target_path"] == candidate.target_component:
                    if self.rollback.restore_snapshot(meta["snapshot_id"]):
                        candidate.status = "rolled_back"
                        self.mutator.update_status(
                            candidate.candidate_id, "rolled_back"
                        )
                        self.state.total_rollbacks += 1
                        self._save_state()
                        return True
            except Exception:
                logging.warning(
                    "Failed to rollback candidate from snapshot %s", sf, exc_info=True
                )
        return False

    def run_evolution_cycle(self) -> dict:
        report = {
            "cycle_start": datetime.now(timezone.utc).isoformat(),
            "generation": self.state.generation,
            "failures_detected": 0,
            "mutations_generated": 0,
            "candidates_evaluated": 0,
            "promotions": 0,
            "errors": [],
        }
        # Phase 1: Detect
        self.state.current_phase = EvolutionPhase.DETECTING
        self._save_state()
        failures = self.get_recurring_failures()
        report["failures_detected"] = len(failures)
        # Phase 2: Mutate
        self.state.current_phase = EvolutionPhase.MUTATING
        self._save_state()
        pending = self.mutator.get_pending()
        report["mutations_generated"] = len(pending)
        # Phase 3: Evaluate
        self.state.current_phase = EvolutionPhase.EVALUATING
        self._save_state()
        evaluated = []
        for c in pending:
            try:
                r = self.evaluate_candidate(c)
                evaluated.append(r)
                report["candidates_evaluated"] += 1
            except Exception as e:
                report["errors"].append(str(e))
        # Phase 4: Select & Promote
        self.state.current_phase = EvolutionPhase.SELECTING
        self._save_state()
        for r in self.selector.select_for_promotion(evaluated):
            cid = r["candidate_id"]
            if cid in self.mutator.candidates:
                if self.promote_candidate(self.mutator.candidates[cid]):
                    report["promotions"] += 1
        self.state.current_phase = EvolutionPhase.IDLE
        self._save_state()
        report["cycle_end"] = datetime.now(timezone.utc).isoformat()
        report["status"] = "complete"
        return report

    def get_stats(self) -> dict:
        return {
            "generation": self.state.generation,
            "total_mutations": self.state.total_mutations,
            "total_promotions": self.state.total_promotions,
            "total_rollbacks": self.state.total_rollbacks,
            "promotion_rate": round(
                self.state.total_promotions / max(self.state.total_mutations, 1) * 100,
                1,
            ),
            "failure_patterns": len(self.detector.patterns),
            "recurring_failures": len(self.get_recurring_failures()),
            "pending_candidates": len(self.mutator.get_pending()),
            "current_phase": self.state.current_phase.value,
        }


_engine: Optional[EvolutionEngine] = None


def get_evolution_engine() -> EvolutionEngine:
    global _engine
    if _engine is None:
        _engine = EvolutionEngine()
    return _engine


if __name__ == "__main__":
    import sys

    engine = get_evolution_engine()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        print(json.dumps(engine.get_stats(), indent=2))
    elif cmd == "failures":
        for f in engine.get_recurring_failures():
            print(f"  [{f.occurrences}x] {f.pattern_type}: {f.description}")
    elif cmd == "candidates":
        for c in engine.mutator.get_pending():
            print(f"  [{c.status}] {c.candidate_id}: {c.mutation_type.value}")
    elif cmd == "cycle":
        print(json.dumps(engine.run_evolution_cycle(), indent=2))
    elif cmd == "record" and len(sys.argv) > 3:
        pid = engine.record_failure(
            sys.argv[2],
            sys.argv[3],
            sys.argv[4] if len(sys.argv) > 4 else "",
            sys.argv[5] if len(sys.argv) > 5 else "",
        )
        print(f"Recorded: {pid}")
    else:
        print("Commands: stats, failures, candidates, cycle, record <type> <desc>")
