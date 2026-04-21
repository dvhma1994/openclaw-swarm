"""
Swarm Intelligence - Emergent coordination from multiple agents
Inspired by: 1Panel-dev/ClawSwarm, JackChen-me/open-multi-agent
"""

import os
import json
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from rich.console import Console
from rich.progress import Progress

from .router import Router, TaskType
from .memory import Memory
from .experience import ExperienceDB

console = Console()


class AgentRole(Enum):
    """Roles in the swarm"""
    COORDINATOR = "coordinator"  # Orchestrates tasks
    WORKER = "worker"  # Executes tasks
    REVIEWER = "reviewer"  # Reviews results
    SPECIALIST = "specialist"  # Domain expert
    AGGREGATOR = "aggregator"  # Combines results


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SwarmTask:
    """A task in the swarm"""
    id: str
    description: str
    priority: TaskPriority
    assigned_agents: List[str]
    status: str  # pending, running, completed, failed
    result: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    dependencies: List[str] = None  # Task IDs that must complete first
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class SwarmAgent:
    """An agent in the swarm"""
    id: str
    name: str
    role: AgentRole
    capabilities: List[str]
    max_concurrent_tasks: int = 3
    current_tasks: int = 0
    total_completed: int = 0
    success_rate: float = 1.0


class SwarmCoordinator:
    """
    Coordinates swarm intelligence
    
    Features:
    - Task decomposition
    - Agent assignment
    - Parallel execution
    - Result aggregation
    - Consensus building
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        memory: Optional[Memory] = None,
        experience: Optional[ExperienceDB] = None
    ):
        self.storage_path = Path(storage_path or os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "swarm"
        ))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.router = Router()
        self.memory = memory or Memory()
        self.experience = experience or ExperienceDB()
        
        self.agents: Dict[str, SwarmAgent] = {}
        self.tasks: Dict[str, SwarmTask] = {}
        self.results: Dict[str, Any] = {}
        
        self._register_default_agents()
    
    def _register_default_agents(self) -> None:
        """Register default swarm agents"""
        default_agents = [
            SwarmAgent(
                id="planner",
                name="Planner",
                role=AgentRole.COORDINATOR,
                capabilities=["planning", "decomposition", "prioritization"],
                max_concurrent_tasks=1
            ),
            SwarmAgent(
                id="coder",
                name="Coder",
                role=AgentRole.WORKER,
                capabilities=["coding", "debugging", "refactoring"],
                max_concurrent_tasks=2
            ),
            SwarmAgent(
                id="reviewer",
                name="Reviewer",
                role=AgentRole.REVIEWER,
                capabilities=["review", "analysis", "quality_check"],
                max_concurrent_tasks=3
            ),
            SwarmAgent(
                id="researcher",
                name="Researcher",
                role=AgentRole.SPECIALIST,
                capabilities=["research", "search", "summarize"],
                max_concurrent_tasks=2
            ),
            SwarmAgent(
                id="aggregator",
                name="Aggregator",
                role=AgentRole.AGGREGATOR,
                capabilities=["synthesis", "combination", "consensus"],
                max_concurrent_tasks=1
            )
        ]
        
        for agent in default_agents:
            self.agents[agent.id] = agent
    
    def register_agent(self, agent: SwarmAgent) -> None:
        """Register a new agent"""
        self.agents[agent.id] = agent
        console.print(f"[green]Agent registered: {agent.name} ({agent.role.value})[/green]")
    
    def decompose_task(
        self,
        task_description: str,
        num_subtasks: int = 3
    ) -> List[SwarmTask]:
        """
        Decompose a complex task into subtasks
        
        Args:
            task_description: The main task
            num_subtasks: Number of subtasks to create
            
        Returns:
            List of subtasks
        """
        prompt = f"""Decompose this task into {num_subtasks} smaller subtasks:

Task: {task_description}

For each subtask, provide:
1. Description
2. Priority (LOW, MEDIUM, HIGH, CRITICAL)
3. Dependencies (if any)

Format each subtask as:
[DESCRIPTION]: ...
[PRIORITY]: ...
[DEPENDENCIES]: ...
"""
        
        response = self.router.call(prompt, TaskType.REASONING)
        
        # Parse response into subtasks
        subtasks = []
        lines = response.strip().split('\n')
        
        current_task = None
        for line in lines:
            line = line.strip()
            if '[DESCRIPTION]:' in line:
                if current_task:
                    subtasks.append(self._create_task(current_task))
                current_task = {'description': line.split('[DESCRIPTION]:')[1].strip()}
            elif '[PRIORITY]:' in line and current_task:
                priority_str = line.split('[PRIORITY]:')[1].strip().upper()
                current_task['priority'] = TaskPriority[priority_str]
            elif '[DEPENDENCIES]:' in line and current_task:
                deps = line.split('[DEPENDENCIES]:')[1].strip()
                current_task['dependencies'] = [d.strip() for d in deps.split(',') if d.strip()]
        
        if current_task:
            subtasks.append(self._create_task(current_task))
        
        # Ensure we have at least one task
        if not subtasks:
            subtasks.append(self._create_task({'description': task_description, 'priority': TaskPriority.MEDIUM}))
        
        return subtasks
    
    def _create_task(self, task_data: Dict[str, Any]) -> SwarmTask:
        """Create a SwarmTask from data"""
        task_id = hashlib.md5(f"{task_data['description']}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        return SwarmTask(
            id=task_id,
            description=task_data.get('description', ''),
            priority=task_data.get('priority', TaskPriority.MEDIUM),
            assigned_agents=[],
            status='pending',
            dependencies=task_data.get('dependencies', [])
        )
    
    def assign_agent(self, task: SwarmTask) -> Optional[str]:
        """Assign best agent for a task"""
        # Find available agents with matching capabilities
        available = [
            agent for agent in self.agents.values()
            if agent.current_tasks < agent.max_concurrent_tasks
        ]
        
        if not available:
            return None
        
        # Check experience for recommendations
        advice = self.experience.get_advice(task.description.split()[0] if task.description else 'general')
        
        # Prefer agents with good experience
        for agent in available:
            if any(cap in ' '.join(advice.get('best_practices', [])) for cap in agent.capabilities):
                return agent.id
        
        # Default: assign worker role agent
        for agent in available:
            if agent.role == AgentRole.WORKER:
                return agent.id
        
        return available[0].id if available else None
    
    def execute_task(
        self,
        task: SwarmTask,
        agent_id: str,
        context: Optional[str] = None
    ) -> str:
        """Execute a single task with an agent"""
        agent = self.agents[agent_id]
        
        # Get relevant memories
        memories = self.memory.find_similar(task.description, limit=3)
        memory_context = "\n".join([f"Past experience: {m.output_data[:200]}" for m in memories])
        
        # Get advice from experience
        advice = self.experience.get_advice(task.description.split()[0] if task.description else 'general')
        
        # Build prompt
        prompt = f"""You are {agent.name}, a {agent.role.value} agent.

Task: {task.description}

Context:
{context or 'No additional context'}

{memory_context if memory_context else ''}

Best practices:
{chr(10).join(advice.get('best_practices', ['None available']))}

Warnings to avoid:
{chr(10).join(advice.get('warnings', ['None available']))}

Please complete this task."""
        
        # Determine task type for routing
        task_type = self._determine_task_type(agent.role)
        
        # Execute
        result = self.router.call(prompt, task_type)
        
        # Record experience
        success = bool(result and not result.startswith('Error'))
        self.experience.record_experience(
            task_type=agent.role.value,
            context=task.description,
            action_taken=f"Executed with {agent.name}",
            result=result[:500],
            success=success
        )
        
        # Store in memory
        self.memory.store(
            agent=agent.name,
            task=task.description,
            input_data=prompt[:500],
            output_data=result[:500],
            success=success
        )
        
        # Update agent stats
        agent.current_tasks -= 1
        agent.total_completed += 1
        if success:
            agent.success_rate = (agent.success_rate * (agent.total_completed - 1) + 1) / agent.total_completed
        else:
            agent.success_rate = agent.success_rate * (agent.total_completed - 1) / agent.total_completed
        
        return result
    
    def _determine_task_type(self, role: AgentRole) -> TaskType:
        """Determine LLM task type from agent role"""
        mapping = {
            AgentRole.COORDINATOR: TaskType.REASONING,
            AgentRole.WORKER: TaskType.CODING,
            AgentRole.REVIEWER: TaskType.REASONING,
            AgentRole.SPECIALIST: TaskType.GENERAL,
            AgentRole.AGGREGATOR: TaskType.REASONING
        }
        return mapping.get(role, TaskType.GENERAL)
    
    def run_swarm(
        self,
        task_description: str,
        max_workers: int = 3,
        decompose: bool = True
    ) -> Dict[str, Any]:
        """
        Run the swarm on a task
        
        Args:
            task_description: The main task
            max_workers: Maximum parallel workers
            decompose: Whether to decompose complex tasks
            
        Returns:
            Results dictionary
        """
        console.print(f"[bold blue]Starting swarm for: {task_description[:50]}...[/bold blue]")
        
        # Decompose if needed
        if decompose:
            subtasks = self.decompose_task(task_description)
            console.print(f"[dim]Decomposed into {len(subtasks)} subtasks[/dim]")
        else:
            subtasks = [self._create_task({'description': task_description, 'priority': TaskPriority.MEDIUM})]
        
        # Store tasks
        for task in subtasks:
            self.tasks[task.id] = task
        
        # Execute tasks with dependency ordering
        results = {}
        completed = set()
        
        with Progress(console=console) as progress:
            task_progress = progress.add_task("[cyan]Executing tasks...", total=len(subtasks))
            
            while len(completed) < len(subtasks):
                # Find tasks ready to execute
                ready = [
                    task for task in subtasks
                    if task.id not in completed
                    and all(dep in completed for dep in task.dependencies)
                ]
                
                if not ready:
                    # Check for circular dependencies
                    remaining = [t for t in subtasks if t.id not in completed]
                    if remaining:
                        console.print(f"[yellow]Warning: Possible circular dependency, forcing execution[/yellow]")
                        ready = remaining[:1]
                    else:
                        break
                
                # Execute ready tasks
                for task in ready[:max_workers]:
                    agent_id = self.assign_agent(task)
                    if not agent_id:
                        console.print(f"[red]No available agent for task {task.id}[/red]")
                        continue
                    
                    task.assigned_agents.append(agent_id)
                    task.status = 'running'
                    task.start_time = datetime.now().isoformat()
                    self.agents[agent_id].current_tasks += 1
                    
                    # Get context from dependencies
                    context = "\n".join([
                        f"Previous result: {results.get(dep, 'N/A')[:200]}"
                        for dep in task.dependencies
                    ]) if task.dependencies else None
                    
                    result = self.execute_task(task, agent_id, context)
                    
                    task.end_time = datetime.now().isoformat()
                    task.status = 'completed'
                    task.result = result
                    results[task.id] = result
                    completed.add(task.id)
                    
                    progress.advance(task_progress)
        
        # Aggregate results if multiple tasks
        if len(subtasks) > 1:
            final_result = self._aggregate_results(results)
        else:
            final_result = list(results.values())[0] if results else "No results"
        
        console.print(f"[green]Swarm completed {len(completed)}/{len(subtasks)} tasks[/green]")
        
        return {
            "task": task_description,
            "subtasks": len(subtasks),
            "completed": len(completed),
            "results": results,
            "final_result": final_result
        }
    
    def _aggregate_results(self, results: Dict[str, str]) -> str:
        """Aggregate multiple results into one"""
        if not results:
            return "No results to aggregate"
        
        if len(results) == 1:
            return list(results.values())[0]
        
        # Use aggregator agent
        prompt = f"""Combine these results into a coherent final answer:

{chr(10).join(f'Result {i+1}: {r}' for i, r in enumerate(results.values()))}

Provide a unified, comprehensive response that incorporates all the results."""
        
        return self.router.call(prompt, TaskType.REASONING)
    
    def get_status(self) -> Dict[str, Any]:
        """Get swarm status"""
        return {
            "agents": {
                agent.id: {
                    "name": agent.name,
                    "role": agent.role.value,
                    "current_tasks": agent.current_tasks,
                    "total_completed": agent.total_completed,
                    "success_rate": round(agent.success_rate, 2)
                }
                for agent in self.agents.values()
            },
            "tasks": {
                task.id: {
                    "description": task.description,
                    "status": task.status,
                    "assigned_agents": task.assigned_agents
                }
                for task in self.tasks.values()
            },
            "memory_stats": self.memory.get_stats(),
            "experience_stats": self.experience.get_stats()
        }


# Convenience function
def run_swarm(task: str, decompose: bool = True) -> Dict[str, Any]:
    """Quick run swarm on task"""
    coordinator = SwarmCoordinator()
    return coordinator.run_swarm(task, decompose=decompose)