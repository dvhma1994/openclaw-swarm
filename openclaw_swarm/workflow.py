"""
OpenClaw Swarm - Workflow Engine
Define and execute multi-step workflows with conditions and dependencies
"""

import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class WorkflowStatus(Enum):
    """Workflow status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(Enum):
    """Step status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ConditionType(Enum):
    """Condition types"""

    ALWAYS = "always"
    ON_SUCCESS = "on_success"
    ON_FAILURE = "on_failure"
    ON_CONDITION = "on_condition"
    PARALLEL = "parallel"


@dataclass
class WorkflowStep:
    """A step in a workflow"""

    id: str
    name: str
    description: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: ConditionType = ConditionType.ALWAYS
    dependencies: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retries: int = 0
    max_retries: int = 3
    timeout: int = 300

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "action": self.action,
            "parameters": self.parameters,
            "condition": self.condition.value,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "retries": self.retries,
        }


@dataclass
class Workflow:
    """A workflow definition"""

    id: str
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    variables: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
            "status": self.status.value,
            "variables": self.variables,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "current_step": self.current_step,
        }


class WorkflowEngine:
    """Execute workflows with dependency management"""

    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.step_handlers: Dict[str, Callable] = {}
        self._running = False

    def register_handler(self, action: str, handler: Callable):
        """Register a handler for an action"""
        self.step_handlers[action] = handler

    def create_workflow(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        variables: Optional[Dict[str, Any]] = None,
    ) -> Workflow:
        """Create a new workflow"""
        workflow = Workflow(
            id="", name=name, description=description, variables=variables or {}
        )

        for step_data in steps:
            step = WorkflowStep(
                id=step_data.get("id", str(uuid.uuid4())),
                name=step_data.get("name", "Unnamed step"),
                description=step_data.get("description", ""),
                action=step_data.get("action", "unknown"),
                parameters=step_data.get("parameters", {}),
                condition=ConditionType(step_data.get("condition", "always")),
                dependencies=step_data.get("dependencies", []),
                max_retries=step_data.get("max_retries", 3),
                timeout=step_data.get("timeout", 300),
            )
            workflow.steps.append(step)

        self.workflows[workflow.id] = workflow
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID"""
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> List[Workflow]:
        """List all workflows"""
        return list(self.workflows.values())

    def _can_execute_step(self, step: WorkflowStep, workflow: Workflow) -> bool:
        """Check if a step can be executed"""
        if step.status != StepStatus.PENDING:
            return False

        for dep_id in step.dependencies:
            dep_step = next((s for s in workflow.steps if s.id == dep_id), None)
            if not dep_step:
                return False
            if dep_step.status != StepStatus.COMPLETED:
                return False

        return True

    def _get_executable_steps(self, workflow: Workflow) -> List[WorkflowStep]:
        """Get steps that can be executed"""
        executable = []

        for step in workflow.steps:
            if self._can_execute_step(step, workflow):
                executable.append(step)

        return executable

    def _execute_step(self, step: WorkflowStep, workflow: Workflow) -> Any:
        """Execute a single step"""
        handler = self.step_handlers.get(step.action)

        if not handler:
            raise ValueError(f"No handler registered for action: {step.action}")

        # Merge workflow variables with step parameters
        params = {**workflow.variables, **step.parameters}

        return handler(**params)

    def run_workflow(self, workflow_id: str) -> Workflow:
        """Run a workflow"""
        workflow = self.workflows.get(workflow_id)

        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()

        # Execute steps in order
        while True:
            executable_steps = self._get_executable_steps(workflow)

            if not executable_steps:
                # Check if all steps are done
                all_done = all(
                    step.status in [StepStatus.COMPLETED, StepStatus.SKIPPED]
                    for step in workflow.steps
                )

                if all_done:
                    workflow.status = WorkflowStatus.COMPLETED
                    workflow.completed_at = datetime.now()
                    break

                # Check for failed steps
                has_failed = any(
                    step.status == StepStatus.FAILED for step in workflow.steps
                )

                if has_failed:
                    workflow.status = WorkflowStatus.FAILED
                    workflow.completed_at = datetime.now()
                    break

                # Wait for more steps
                break

            # Execute one step at a time (sequential)
            step = executable_steps[0]
            workflow.current_step = step.id
            step.status = StepStatus.RUNNING
            step.started_at = datetime.now()

            try:
                result = self._execute_step(step, workflow)
                step.result = result
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.now()

                # Update workflow variables with step result
                if isinstance(result, dict):
                    workflow.variables.update(result)

            except Exception as e:
                step.error = str(e)
                step.status = StepStatus.FAILED
                step.completed_at = datetime.now()

                # Check condition
                if step.condition == ConditionType.ON_FAILURE:
                    # Continue on failure
                    pass
                else:
                    # Fail workflow
                    workflow.status = WorkflowStatus.FAILED
                    workflow.completed_at = datetime.now()
                    break

        return workflow

    def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow"""
        workflow = self.workflows.get(workflow_id)

        if workflow and workflow.status == WorkflowStatus.RUNNING:
            workflow.status = WorkflowStatus.PAUSED
            return True

        return False

    def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow"""
        workflow = self.workflows.get(workflow_id)

        if workflow and workflow.status == WorkflowStatus.PAUSED:
            workflow.status = WorkflowStatus.RUNNING
            return True

        return False

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a workflow"""
        workflow = self.workflows.get(workflow_id)

        if workflow and workflow.status in [
            WorkflowStatus.RUNNING,
            WorkflowStatus.PAUSED,
        ]:
            workflow.status = WorkflowStatus.CANCELLED
            workflow.completed_at = datetime.now()
            return True

        return False

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            return True
        return False

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status"""
        workflow = self.workflows.get(workflow_id)

        if not workflow:
            return None

        return {
            "id": workflow.id,
            "name": workflow.name,
            "status": workflow.status.value,
            "total_steps": len(workflow.steps),
            "completed_steps": sum(
                1 for s in workflow.steps if s.status == StepStatus.COMPLETED
            ),
            "failed_steps": sum(
                1 for s in workflow.steps if s.status == StepStatus.FAILED
            ),
            "current_step": workflow.current_step,
            "started_at": (
                workflow.started_at.isoformat() if workflow.started_at else None
            ),
            "completed_at": (
                workflow.completed_at.isoformat() if workflow.completed_at else None
            ),
        }

    def get_step_status(
        self, workflow_id: str, step_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get step status"""
        workflow = self.workflows.get(workflow_id)

        if not workflow:
            return None

        step = next((s for s in workflow.steps if s.id == step_id), None)

        if not step:
            return None

        return step.to_dict()

    def export_workflow(self, workflow_id: str) -> Optional[str]:
        """Export workflow as JSON"""
        workflow = self.workflows.get(workflow_id)

        if not workflow:
            return None

        return json.dumps(workflow.to_dict(), indent=2)

    def import_workflow(self, workflow_json: str) -> Workflow:
        """Import workflow from JSON"""
        data = json.loads(workflow_json)

        steps = []
        for step_data in data.get("steps", []):
            step = WorkflowStep(
                id=step_data.get("id", str(uuid.uuid4())),
                name=step_data.get("name", "Unnamed step"),
                description=step_data.get("description", ""),
                action=step_data.get("action", "unknown"),
                parameters=step_data.get("parameters", {}),
                condition=ConditionType(step_data.get("condition", "always")),
                dependencies=step_data.get("dependencies", []),
                max_retries=step_data.get("max_retries", 3),
                timeout=step_data.get("timeout", 300),
            )
            steps.append(step)

        workflow = Workflow(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Imported workflow"),
            description=data.get("description", ""),
            steps=steps,
            variables=data.get("variables", {}),
        )

        self.workflows[workflow.id] = workflow
        return workflow


# Pre-defined workflow templates
def create_code_review_workflow(engine: WorkflowEngine) -> Workflow:
    """Create a code review workflow"""
    return engine.create_workflow(
        name="Code Review",
        description="Review code for quality and security",
        steps=[
            {
                "id": "analyze",
                "name": "Analyze Code",
                "description": "Analyze code structure and complexity",
                "action": "analyze_code",
                "condition": "always",
            },
            {
                "id": "check_style",
                "name": "Check Style",
                "description": "Check code style and formatting",
                "action": "check_style",
                "condition": "on_success",
                "dependencies": ["analyze"],
            },
            {
                "id": "check_security",
                "name": "Check Security",
                "description": "Check for security vulnerabilities",
                "action": "check_security",
                "condition": "on_success",
                "dependencies": ["analyze"],
            },
            {
                "id": "generate_report",
                "name": "Generate Report",
                "description": "Generate review report",
                "action": "generate_report",
                "condition": "always",
                "dependencies": ["check_style", "check_security"],
            },
        ],
    )


def create_data_pipeline_workflow(engine: WorkflowEngine) -> Workflow:
    """Create a data processing pipeline workflow"""
    return engine.create_workflow(
        name="Data Pipeline",
        description="Process and analyze data",
        steps=[
            {
                "id": "extract",
                "name": "Extract Data",
                "description": "Extract data from source",
                "action": "extract_data",
                "condition": "always",
            },
            {
                "id": "transform",
                "name": "Transform Data",
                "description": "Transform and clean data",
                "action": "transform_data",
                "condition": "on_success",
                "dependencies": ["extract"],
            },
            {
                "id": "validate",
                "name": "Validate Data",
                "description": "Validate data quality",
                "action": "validate_data",
                "condition": "on_success",
                "dependencies": ["transform"],
            },
            {
                "id": "load",
                "name": "Load Data",
                "description": "Load data to destination",
                "action": "load_data",
                "condition": "on_success",
                "dependencies": ["validate"],
            },
        ],
    )
