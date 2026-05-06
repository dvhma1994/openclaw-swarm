"""
Multi-Agent Swarm Orchestration
================================
Coordinates multiple agents working in parallel on tasks.
Inspired by: MassGen (consensus voting), Claude Squad (workspace isolation),
             Plandex (autonomy control), Skynet (LangGraph autopilot).
"""

import json
import os
import hashlib
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(
    os.environ.get(
        "OPENCLAW_DIRECTOR_DIR", Path.home() / ".openclaw" / "workspaces" / "director"
    )
)
SWARM_DIR = BASE_DIR / "swarm_orchestrator"
SWARM_DIR.mkdir(parents=True, exist_ok=True)
SWARM_LOG = SWARM_DIR / "swarm_log.jsonl"


class AgentRole(str, Enum):
    CODER = "coder"
    REVIEWER = "reviewer"
    PLANNER = "planner"
    DEBUGGER = "debugger"
    RESEARCHER = "researcher"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VoteStrategy(str, Enum):
    MAJORITY = "majority"
    BEST_SCORE = "best_score"
    CONSENSUS = "consensus"
    WEIGHTED = "weighted"


@dataclass
class SwarmAgent:
    agent_id: str
    role: AgentRole
    model: str = "sonnet"
    reputation: float = 1.0
    tasks_completed: int = 0
    tasks_correct: int = 0
    last_active: str = ""

    def to_dict(self):
        return {**asdict(self), "role": self.role.value}

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        data["role"] = AgentRole(data["role"])
        return cls(**data)


@dataclass
class SwarmTask:
    task_id: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    required_roles: list = field(default_factory=list)
    min_agents: int = 2
    max_agents: int = 4
    timeout_seconds: int = 300
    status: str = "pending"
    assigned_agents: list = field(default_factory=list)
    results: list = field(default_factory=list)
    winner: Optional[str] = None
    created_at: str = ""
    completed_at: str = ""

    def to_dict(self):
        return {**asdict(self), "priority": self.priority.value}


@dataclass
class AgentResult:
    agent_id: str
    task_id: str
    content: str = ""
    score: float = 0.0
    confidence: float = 0.5
    execution_time_ms: int = 0
    error: str = ""
    vote_weight: float = 1.0

    def to_dict(self):
        return asdict(self)


class CollaborationHub:
    """Shared state hub for real-time collaboration between agents."""

    def __init__(self):
        self.observations: Dict[str, list] = {}
        self.insights: Dict[str, list] = {}
        self._lock = threading.Lock()

    def post_observation(self, task_id: str, agent_id: str, content: str):
        with self._lock:
            self.observations.setdefault(task_id, []).append(
                {
                    "agent_id": agent_id,
                    "content": content,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

    def post_insight(self, task_id: str, agent_id: str, insight: str):
        with self._lock:
            self.insights.setdefault(task_id, []).append(
                {
                    "agent_id": agent_id,
                    "insight": insight,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

    def get_observations(self, task_id: str, exclude_agent: str = "") -> list:
        with self._lock:
            obs = self.observations.get(task_id, [])
            if exclude_agent:
                obs = [o for o in obs if o["agent_id"] != exclude_agent]
            return list(obs)

    def get_insights(self, task_id: str) -> list:
        with self._lock:
            return list(self.insights.get(task_id, []))

    def clear_task(self, task_id: str):
        with self._lock:
            self.observations.pop(task_id, None)
            self.insights.pop(task_id, None)


class ConsensusVoter:
    """Determines the best result from multiple agents using voting strategies."""

    def __init__(self, strategy: VoteStrategy = VoteStrategy.BEST_SCORE):
        self.strategy = strategy

    def vote(self, results: List[AgentResult]) -> Optional[AgentResult]:
        if not results:
            return None
        valid = [r for r in results if not r.error]
        if not valid:
            return results[0]
        if self.strategy == VoteStrategy.MAJORITY:
            return self._majority_vote(valid)
        elif self.strategy == VoteStrategy.BEST_SCORE:
            return self._best_score_vote(valid)
        elif self.strategy == VoteStrategy.CONSENSUS:
            return self._consensus_vote(valid)
        elif self.strategy == VoteStrategy.WEIGHTED:
            return self._weighted_vote(valid)
        return self._best_score_vote(valid)

    def _majority_vote(self, results: List[AgentResult]) -> AgentResult:
        groups: Dict[str, list] = {}
        for r in results:
            h = hashlib.md5(r.content.encode()).hexdigest()[:8]
            groups.setdefault(h, []).append(r)
        return max(groups.values(), key=lambda g: len(g))[0]

    def _best_score_vote(self, results: List[AgentResult]) -> AgentResult:
        return max(results, key=lambda r: r.score * r.confidence)

    def _consensus_vote(self, results: List[AgentResult]) -> Optional[AgentResult]:
        high = [r for r in results if r.score >= 0.7]
        if len(high) < len(results) and len(results) >= 2:
            return None
        return self._best_score_vote(high) if high else None

    def _weighted_vote(self, results: List[AgentResult]) -> AgentResult:
        return max(results, key=lambda r: r.score * r.vote_weight * r.confidence)


class SwarmOrchestrator:
    """Main orchestrator for multi-agent swarms."""

    def __init__(self, base_dir: Path = SWARM_DIR):
        self.base_dir = base_dir
        self.agents: Dict[str, SwarmAgent] = {}
        self.tasks: Dict[str, SwarmTask] = {}
        self.hub = CollaborationHub()
        self.voter = ConsensusVoter()

    def register_agent(
        self, agent_id: str, role: AgentRole, model: str = "sonnet"
    ) -> SwarmAgent:
        agent = SwarmAgent(
            agent_id=agent_id,
            role=role,
            model=model,
            last_active=datetime.now(timezone.utc).isoformat(),
        )
        self.agents[agent_id] = agent
        return agent

    def submit_task(
        self,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        required_roles: list = None,
        min_agents: int = 2,
        max_agents: int = 4,
        timeout_seconds: int = 300,
    ) -> SwarmTask:
        task_id = f"task_{hashlib.md5(description.encode()).hexdigest()[:8]}_{int(time.time())}"
        task = SwarmTask(
            task_id=task_id,
            description=description,
            priority=priority,
            required_roles=required_roles or [AgentRole.CODER.value],
            min_agents=min_agents,
            max_agents=max_agents,
            timeout_seconds=timeout_seconds,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.tasks[task_id] = task
        return task

    def _select_agents(self, task: SwarmTask) -> List[SwarmAgent]:
        eligible = [
            a
            for a in self.agents.values()
            if a.role.value in task.required_roles or not task.required_roles
        ]
        eligible.sort(key=lambda a: a.reputation, reverse=True)
        return eligible[: task.max_agents]

    def execute_agent(
        self, agent: SwarmAgent, task: SwarmTask, executor_fn: Callable
    ) -> AgentResult:
        start = time.time()
        try:
            other_obs = self.hub.get_observations(
                task.task_id, exclude_agent=agent.agent_id
            )
            context = {
                "observations": other_obs,
                "insights": self.hub.get_insights(task.task_id),
            }
            result_content = executor_fn(agent, task, context)
            elapsed_ms = int((time.time() - start) * 1000)
            result = AgentResult(
                agent_id=agent.agent_id,
                task_id=task.task_id,
                content=str(result_content)[:5000],
                confidence=0.7,
                execution_time_ms=elapsed_ms,
                vote_weight=agent.reputation,
            )
            self.hub.post_observation(
                task.task_id, agent.agent_id, str(result_content)[:500]
            )
            agent.tasks_completed += 1
            agent.last_active = datetime.now(timezone.utc).isoformat()
            return result
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            return AgentResult(
                agent_id=agent.agent_id,
                task_id=task.task_id,
                error=str(e),
                execution_time_ms=elapsed_ms,
                vote_weight=agent.reputation,
            )

    def run_task(self, task: SwarmTask, executor_fn: Callable) -> dict:
        agents = self._select_agents(task)
        if len(agents) < task.min_agents:
            task.status = "failed"
            return {
                "task_id": task.task_id,
                "status": "failed",
                "error": f"Not enough agents ({len(agents)}/{task.min_agents})",
            }
        task.status = "running"
        task.assigned_agents = [a.agent_id for a in agents]
        results = []
        with ThreadPoolExecutor(max_workers=len(agents)) as pool:
            futures = {
                pool.submit(self.execute_agent, a, task, executor_fn): a for a in agents
            }
            for future in as_completed(futures, timeout=task.timeout_seconds):
                try:
                    results.append(future.result(timeout=task.timeout_seconds))
                except Exception as e:
                    results.append(
                        AgentResult(
                            agent_id=futures[future].agent_id,
                            task_id=task.task_id,
                            error=str(e),
                        )
                    )
        task.results = [r.to_dict() for r in results]
        winner = self.voter.vote(results)
        if winner:
            task.winner = winner.agent_id
            task.status = "completed"
            if winner.agent_id in self.agents:
                a = self.agents[winner.agent_id]
                a.tasks_correct += 1
                a.reputation = min(2.0, a.reputation + 0.1)
        else:
            task.status = "no_consensus"
        task.completed_at = datetime.now(timezone.utc).isoformat()
        self.hub.clear_task(task.task_id)
        with open(SWARM_LOG, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "task_id": task.task_id,
                        "status": task.status,
                        "agents": len(agents),
                        "winner": task.winner,
                    },
                    default=str,
                )
                + "\n"
            )
        return {
            "task_id": task.task_id,
            "status": task.status,
            "winner": task.winner,
            "agents_used": [a.agent_id for a in agents],
            "winner_content": winner.content[:500] if winner else None,
        }

    def run_parallel(
        self,
        description: str,
        executor_fn: Callable,
        min_agents: int = 2,
        max_agents: int = 4,
    ) -> dict:
        task = self.submit_task(
            description, min_agents=min_agents, max_agents=max_agents
        )
        return self.run_task(task, executor_fn)

    def get_stats(self) -> dict:
        return {
            "registered_agents": len(self.agents),
            "total_tasks": len(self.tasks),
            "completed": len(
                [t for t in self.tasks.values() if t.status == "completed"]
            ),
            "agents": {
                a.agent_id: {
                    "role": a.role.value,
                    "rep": a.reputation,
                    "tasks": a.tasks_completed,
                    "correct": a.tasks_correct,
                }
                for a in self.agents.values()
            },
        }


_orchestrator: Optional[SwarmOrchestrator] = None


def get_swarm() -> SwarmOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SwarmOrchestrator()
    return _orchestrator


if __name__ == "__main__":
    import sys

    swarm = get_swarm()
    swarm.register_agent("director", AgentRole.CODER, "sonnet")
    swarm.register_agent("qa", AgentRole.REVIEWER, "haiku")
    swarm.register_agent("expert", AgentRole.PLANNER, "opus")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        print(json.dumps(swarm.get_stats(), indent=2))
    elif cmd == "agents":
        for a in swarm.agents.values():
            print(f"  {a.agent_id}: role={a.role.value} rep={a.reputation}")
    else:
        print("Commands: stats, agents")
