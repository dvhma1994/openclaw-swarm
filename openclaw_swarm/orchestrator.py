"""
Orchestrator - Multi-Agent Coordination
Inspired by ai-orchestrator - Role-based execution
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from rich.console import Console
from rich.progress import Progress

from .router import Router, TaskType

console = Console()


@dataclass
class AgentResult:
    """Result from an agent execution"""

    agent_name: str
    success: bool
    output: str
    duration_ms: int
    error: Optional[str] = None


@dataclass
class Agent:
    """Agent definition"""

    name: str
    role: str
    model_type: str
    system_prompt: str
    max_tokens: int = 2000


class Orchestrator:
    """Coordinates multiple agents to complete tasks"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), "..", "config", "agents.yaml"
        )
        self.config = self._load_config()
        self.agents = self._parse_agents()
        self.router = Router()
        self.history: List[Dict[str, Any]] = []

    def _load_config(self) -> Dict[str, Any]:
        """Load agent configuration from YAML"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            console.print("[yellow]Config not found, using defaults[/yellow]")
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration"""
        return {
            "agents": {
                "planner": {
                    "name": "Planner",
                    "role": "Plan and break down tasks",
                    "model_type": "reasoning",
                    "system_prompt": "You are a task planner. Break down complex tasks into smaller, actionable steps.",
                    "max_tokens": 2000,
                },
                "coder": {
                    "name": "Coder",
                    "role": "Write and modify code",
                    "model_type": "coding",
                    "system_prompt": "You are an expert programmer. Write clean, efficient, and well-documented code.",
                    "max_tokens": 4000,
                },
                "reviewer": {
                    "name": "Reviewer",
                    "role": "Review and improve code",
                    "model_type": "reasoning",
                    "system_prompt": "You are a code reviewer. Analyze code for bugs, security issues, and improvements.",
                    "max_tokens": 2000,
                },
            },
            "orchestrator": {
                "max_parallel": 3,
                "agent_timeout": 300,
                "retry_failed": True,
            },
            "workflow": {"default": ["planner", "coder", "reviewer"]},
        }

    def _parse_agents(self) -> Dict[str, Agent]:
        """Parse agent definitions"""
        agents = {}
        for agent_id, cfg in self.config.get("agents", {}).items():
            agents[agent_id] = Agent(
                name=cfg.get("name", agent_id),
                role=cfg.get("role", ""),
                model_type=cfg.get("model_type", "general"),
                system_prompt=cfg.get("system_prompt", ""),
                max_tokens=cfg.get("max_tokens", 2000),
            )
        return agents

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)

    def list_agents(self) -> List[str]:
        """List available agent IDs"""
        return list(self.agents.keys())

    def run_agent(
        self, agent_id: str, prompt: str, context: Optional[str] = None
    ) -> AgentResult:
        """Run a single agent"""
        agent = self.get_agent(agent_id)
        if not agent:
            return AgentResult(
                agent_name=agent_id,
                success=False,
                output="",
                duration_ms=0,
                error=f"Agent '{agent_id}' not found",
            )

        start_time = datetime.now()

        try:
            # Build full prompt
            full_prompt = agent.system_prompt
            if context:
                full_prompt += f"\n\nContext:\n{context}"
            full_prompt += f"\n\nTask:\n{prompt}"

            # Call router
            task_type = (
                TaskType(agent.model_type)
                if agent.model_type in [t.value for t in TaskType]
                else TaskType.GENERAL
            )
            output = self.router.call(full_prompt, task_type)

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return AgentResult(
                agent_name=agent.name,
                success=True,
                output=output,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return AgentResult(
                agent_name=agent.name,
                success=False,
                output="",
                duration_ms=duration_ms,
                error=str(e),
            )

    def run_workflow(
        self,
        prompt: str,
        workflow: Optional[List[str]] = None,
        show_progress: bool = True,
    ) -> Dict[str, AgentResult]:
        """
        Run a workflow of agents

        Args:
            prompt: The main prompt/task
            workflow: List of agent IDs to run in sequence
            show_progress: Show progress bar

        Returns:
            Dict of agent_id -> AgentResult
        """
        # Get default workflow if not specified
        if workflow is None:
            workflow = self.config.get("workflow", {}).get(
                "default", ["planner", "coder", "reviewer"]
            )

        results: Dict[str, AgentResult] = {}
        context = ""

        if show_progress:
            with Progress(console=console) as progress:
                task = progress.add_task(
                    "[cyan]Running workflow...", total=len(workflow)
                )

                for agent_id in workflow:
                    progress.update(task, description=f"[cyan]Running {agent_id}...")

                    result = self.run_agent(
                        agent_id, prompt, context if context else None
                    )
                    results[agent_id] = result

                    if result.success:
                        context = result.output

                    progress.advance(task)
        else:
            for agent_id in workflow:
                result = self.run_agent(agent_id, prompt, context if context else None)
                results[agent_id] = result

                if result.success:
                    context = result.output

        # Save to history
        self._save_history(prompt, workflow, results)

        return results

    def run_parallel(
        self, prompt: str, agents: Optional[List[str]] = None, max_workers: int = 3
    ) -> Dict[str, AgentResult]:
        """
        Run multiple agents in parallel

        Args:
            prompt: The prompt to send to all agents
            agents: List of agent IDs (default: all agents)
            max_workers: Maximum parallel workers

        Returns:
            Dict of agent_id -> AgentResult
        """
        if agents is None:
            agents = list(self.agents.keys())[:max_workers]

        results: Dict[str, AgentResult] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.run_agent, agent_id, prompt): agent_id
                for agent_id in agents
            }

            for future in as_completed(futures):
                agent_id = futures[future]
                try:
                    results[agent_id] = future.result()
                except Exception as e:
                    results[agent_id] = AgentResult(
                        agent_name=agent_id,
                        success=False,
                        output="",
                        duration_ms=0,
                        error=str(e),
                    )

        return results

    def _save_history(
        self, prompt: str, workflow: List[str], results: Dict[str, AgentResult]
    ) -> None:
        """Save workflow execution to history"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "workflow": workflow,
            "results": {
                agent_id: {
                    "success": r.success,
                    "output": r.output,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                }
                for agent_id, r in results.items()
            },
        }
        self.history.append(entry)

        # Optionally save to file
        history_file = Path("data/history.json")
        history_file.parent.mkdir(parents=True, exist_ok=True)

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)


# Convenience function
def orchestrate(
    prompt: str, workflow: Optional[List[str]] = None
) -> Dict[str, AgentResult]:
    """Quick orchestration"""
    orchestrator = Orchestrator()
    return orchestrator.run_workflow(prompt, workflow)
