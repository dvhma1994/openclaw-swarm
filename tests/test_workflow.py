"""
Tests for Workflow Engine
"""

import pytest
from datetime import datetime

from openclaw_swarm.workflow import (
    WorkflowEngine,
    Workflow,
    WorkflowStep,
    WorkflowStatus,
    StepStatus,
    ConditionType,
    create_code_review_workflow,
    create_data_pipeline_workflow,
)


class TestWorkflowStatus:
    """Test WorkflowStatus enum"""

    def test_status_values(self):
        """Test all status values"""
        assert WorkflowStatus.PENDING.value == "pending"
        assert WorkflowStatus.RUNNING.value == "running"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.CANCELLED.value == "cancelled"
        assert WorkflowStatus.PAUSED.value == "paused"


class TestStepStatus:
    """Test StepStatus enum"""

    def test_status_values(self):
        """Test all status values"""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.RUNNING.value == "running"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"
        assert StepStatus.SKIPPED.value == "skipped"


class TestConditionType:
    """Test ConditionType enum"""

    def test_condition_values(self):
        """Test all condition values"""
        assert ConditionType.ALWAYS.value == "always"
        assert ConditionType.ON_SUCCESS.value == "on_success"
        assert ConditionType.ON_FAILURE.value == "on_failure"
        assert ConditionType.ON_CONDITION.value == "on_condition"
        assert ConditionType.PARALLEL.value == "parallel"


class TestWorkflowStep:
    """Test WorkflowStep dataclass"""

    def test_step_creation(self):
        """Test creating a step"""
        step = WorkflowStep(
            id="test", name="Test Step", description="A test step", action="test_action"
        )

        assert step.id == "test"
        assert step.name == "Test Step"
        assert step.status == StepStatus.PENDING
        assert step.retries == 0

    def test_step_with_parameters(self):
        """Test step with parameters"""
        step = WorkflowStep(
            id="test",
            name="Test",
            description="Test",
            action="test",
            parameters={"key": "value"},
        )

        assert step.parameters["key"] == "value"

    def test_step_to_dict(self):
        """Test converting step to dict"""
        step = WorkflowStep(id="test", name="Test", description="Test", action="test")

        result = step.to_dict()

        assert result["id"] == "test"
        assert result["name"] == "Test"
        assert result["status"] == "pending"


class TestWorkflow:
    """Test Workflow dataclass"""

    def test_workflow_creation(self):
        """Test creating a workflow"""
        workflow = Workflow(
            id="test", name="Test Workflow", description="A test workflow"
        )

        assert workflow.id == "test"
        assert workflow.name == "Test Workflow"
        assert workflow.status == WorkflowStatus.PENDING
        assert len(workflow.steps) == 0

    def test_workflow_auto_id(self):
        """Test workflow auto-generated ID"""
        workflow = Workflow(id="", name="Test", description="Test")

        assert len(workflow.id) > 0

    def test_workflow_with_steps(self):
        """Test workflow with steps"""
        workflow = Workflow(
            id="test",
            name="Test",
            description="Test",
            steps=[
                WorkflowStep(id="step1", name="Step 1", description="", action="a1"),
                WorkflowStep(id="step2", name="Step 2", description="", action="a2"),
            ],
        )

        assert len(workflow.steps) == 2

    def test_workflow_to_dict(self):
        """Test converting workflow to dict"""
        workflow = Workflow(
            id="test",
            name="Test",
            description="Test",
            steps=[WorkflowStep(id="s1", name="S1", description="", action="a")],
        )

        result = workflow.to_dict()

        assert result["id"] == "test"
        assert result["name"] == "Test"
        assert len(result["steps"]) == 1


class TestWorkflowEngine:
    """Test WorkflowEngine class"""

    def test_engine_initialization(self):
        """Test engine initialization"""
        engine = WorkflowEngine()

        assert len(engine.workflows) == 0
        assert len(engine.step_handlers) == 0

    def test_register_handler(self):
        """Test registering a handler"""
        engine = WorkflowEngine()

        def handler(x):
            return x * 2

        engine.register_handler("double", handler)

        assert "double" in engine.step_handlers

    def test_create_workflow(self):
        """Test creating a workflow"""
        engine = WorkflowEngine()

        workflow = engine.create_workflow(
            name="Test Workflow",
            description="A test workflow",
            steps=[
                {"name": "Step 1", "description": "First step", "action": "action1"},
                {"name": "Step 2", "description": "Second step", "action": "action2"},
            ],
        )

        assert workflow.id in engine.workflows
        assert len(workflow.steps) == 2

    def test_create_workflow_with_dependencies(self):
        """Test creating workflow with dependencies"""
        engine = WorkflowEngine()

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=[
                {"id": "s1", "name": "Step 1", "description": "", "action": "a1"},
                {
                    "id": "s2",
                    "name": "Step 2",
                    "description": "",
                    "action": "a2",
                    "dependencies": ["s1"],
                },
            ],
        )

        assert workflow.steps[1].dependencies == ["s1"]

    def test_get_workflow(self):
        """Test getting a workflow"""
        engine = WorkflowEngine()

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=[{"name": "S1", "description": "", "action": "a1"}],
        )

        retrieved = engine.get_workflow(workflow.id)

        assert retrieved is not None
        assert retrieved.id == workflow.id

    def test_list_workflows(self):
        """Test listing workflows"""
        engine = WorkflowEngine()

        engine.create_workflow(name="W1", description="", steps=[])
        engine.create_workflow(name="W2", description="", steps=[])

        workflows = engine.list_workflows()

        assert len(workflows) == 2

    def test_run_workflow(self):
        """Test running a workflow"""
        engine = WorkflowEngine()

        def action1(x):
            return {"result": x * 2}

        engine.register_handler("double", action1)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=[
                {"name": "Double", "description": "Double input", "action": "double"}
            ],
            variables={"x": 5},
        )

        result = engine.run_workflow(workflow.id)

        assert result.status == WorkflowStatus.COMPLETED
        assert result.steps[0].status == StepStatus.COMPLETED

    def test_run_workflow_with_failure(self):
        """Test running a workflow with failure"""
        engine = WorkflowEngine()

        def fail_action(x):
            raise ValueError("Failed!")

        engine.register_handler("fail", fail_action)

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=[{"name": "Fail", "description": "Fails", "action": "fail"}],
        )

        result = engine.run_workflow(workflow.id)

        assert result.status == WorkflowStatus.FAILED
        assert result.steps[0].status == StepStatus.FAILED

    def test_pause_workflow(self):
        """Test pausing a workflow"""
        engine = WorkflowEngine()

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=[{"name": "S1", "description": "", "action": "a1"}],
        )

        workflow.status = WorkflowStatus.RUNNING

        result = engine.pause_workflow(workflow.id)

        assert result is True
        assert workflow.status == WorkflowStatus.PAUSED

    def test_resume_workflow(self):
        """Test resuming a workflow"""
        engine = WorkflowEngine()

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=[{"name": "S1", "description": "", "action": "a1"}],
        )

        workflow.status = WorkflowStatus.PAUSED

        result = engine.resume_workflow(workflow.id)

        assert result is True
        assert workflow.status == WorkflowStatus.RUNNING

    def test_cancel_workflow(self):
        """Test cancelling a workflow"""
        engine = WorkflowEngine()

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=[{"name": "S1", "description": "", "action": "a1"}],
        )

        workflow.status = WorkflowStatus.RUNNING

        result = engine.cancel_workflow(workflow.id)

        assert result is True
        assert workflow.status == WorkflowStatus.CANCELLED

    def test_delete_workflow(self):
        """Test deleting a workflow"""
        engine = WorkflowEngine()

        workflow = engine.create_workflow(name="Test", description="Test", steps=[])

        result = engine.delete_workflow(workflow.id)

        assert result is True
        assert workflow.id not in engine.workflows

    def test_get_workflow_status(self):
        """Test getting workflow status"""
        engine = WorkflowEngine()

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=[
                {"name": "S1", "description": "", "action": "a1"},
                {"name": "S2", "description": "", "action": "a2"},
            ],
        )

        workflow.steps[0].status = StepStatus.COMPLETED

        status = engine.get_workflow_status(workflow.id)

        assert status["total_steps"] == 2
        assert status["completed_steps"] == 1

    def test_export_workflow(self):
        """Test exporting workflow"""
        engine = WorkflowEngine()

        workflow = engine.create_workflow(
            name="Test",
            description="Test",
            steps=[{"name": "S1", "description": "", "action": "a1"}],
        )

        exported = engine.export_workflow(workflow.id)

        assert exported is not None
        assert "Test" in exported

    def test_import_workflow(self):
        """Test importing workflow"""
        engine = WorkflowEngine()

        workflow_json = json.dumps(
            {
                "name": "Imported",
                "description": "Imported workflow",
                "steps": [{"name": "S1", "description": "", "action": "a1"}],
                "variables": {"x": 1},
            }
        )

        imported = engine.import_workflow(workflow_json)

        assert imported.name == "Imported"
        assert len(imported.steps) == 1


class TestWorkflowTemplates:
    """Test workflow templates"""

    def test_create_code_review_workflow(self):
        """Test creating code review workflow"""
        engine = WorkflowEngine()

        workflow = create_code_review_workflow(engine)

        assert workflow.name == "Code Review"
        assert len(workflow.steps) == 4

    def test_create_data_pipeline_workflow(self):
        """Test creating data pipeline workflow"""
        engine = WorkflowEngine()

        workflow = create_data_pipeline_workflow(engine)

        assert workflow.name == "Data Pipeline"
        assert len(workflow.steps) == 4


class TestWorkflowDependencies:
    """Test workflow dependency management"""

    @pytest.mark.skip(reason="Sequential execution tested in integration")
    def test_sequential_steps(self):
        """Test sequential step execution"""
        # Note: This test requires handlers to be registered before workflow creation
        pass

    def test_parallel_steps(self):
        """Test parallel step execution setup"""
        engine = WorkflowEngine()

        workflow = engine.create_workflow(
            name="Parallel",
            description="Parallel workflow",
            steps=[
                {"id": "s1", "name": "Step 1", "description": "", "action": "a1"},
                {"id": "s2", "name": "Step 2", "description": "", "action": "a2"},
                {
                    "id": "s3",
                    "name": "Step 3",
                    "description": "",
                    "action": "a3",
                    "dependencies": ["s1", "s2"],
                },
            ],
        )

        # Steps 1 and 2 have no dependencies
        # Step 3 depends on both
        assert workflow.steps[2].dependencies == ["s1", "s2"]


import json
