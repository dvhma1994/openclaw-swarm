"""
Example: Workflow Engine
========================

This example shows how to use the workflow engine.
"""

from openclaw_swarm import (
    WorkflowEngine,
    StepStatus,
    create_code_review_workflow,
    create_data_pipeline_workflow,
)


def main():
    print("=" * 60)
    print("OpenClaw Swarm - Workflow Engine Example")
    print("=" * 60)

    # 1. Create Workflow Engine
    print("\n1. Create Workflow Engine")
    print("-" * 40)

    engine = WorkflowEngine()

    print(f"Workflows: {len(engine.workflows)}")
    print(f"Handlers: {len(engine.step_handlers)}")

    # 2. Register Step Handlers
    print("\n2. Register Step Handlers")
    print("-" * 40)

    def analyze_code(code: str):
        print(f"  Analyzing code: {len(code)} chars")
        return {"lines": code.count("\n") + 1}

    def check_style(result: dict):
        print(f"  Checking style for {result['lines']} lines")
        return {"style": "pass"}

    def check_security(result: dict):
        print(f"  Checking security for {result['lines']} lines")
        return {"security": "pass"}

    def generate_report(style: dict, security: dict):
        print("  Generating report")
        return {"report": "All checks passed"}

    engine.register_handler("analyze_code", analyze_code)
    engine.register_handler("check_style", check_style)
    engine.register_handler("check_security", check_security)
    engine.register_handler("generate_report", generate_report)

    print(f"Registered handlers: {list(engine.step_handlers.keys())}")

    # 3. Create Custom Workflow
    print("\n3. Create Custom Workflow")
    print("-" * 40)

    workflow = engine.create_workflow(
        name="Custom Review",
        description="Custom code review workflow",
        steps=[
            {
                "id": "analyze",
                "name": "Analyze Code",
                "description": "Analyze code structure",
                "action": "analyze_code",
                "condition": "always",
            },
            {
                "id": "style",
                "name": "Check Style",
                "description": "Check code style",
                "action": "check_style",
                "condition": "on_success",
                "dependencies": ["analyze"],
            },
            {
                "id": "security",
                "name": "Check Security",
                "description": "Check for vulnerabilities",
                "action": "check_security",
                "condition": "on_success",
                "dependencies": ["analyze"],
            },
            {
                "id": "report",
                "name": "Generate Report",
                "description": "Generate final report",
                "action": "generate_report",
                "condition": "always",
                "dependencies": ["style", "security"],
            },
        ],
        variables={"code": "def hello():\n    print('Hello')\n"},
    )

    print(f"Workflow ID: {workflow.id}")
    print(f"Workflow name: {workflow.name}")
    print(f"Steps: {len(workflow.steps)}")

    # 4. Run Workflow
    print("\n4. Run Workflow")
    print("-" * 40)

    result = engine.run_workflow(workflow.id)

    print(f"\nWorkflow status: {result.status.value}")
    print(
        f"Steps completed: {sum(1 for s in result.steps if s.status == StepStatus.COMPLETED)}"
    )

    # 5. Get Workflow Status
    print("\n5. Get Workflow Status")
    print("-" * 40)

    status = engine.get_workflow_status(workflow.id)

    print(f"Status: {status['status']}")
    print(f"Total steps: {status['total_steps']}")
    print(f"Completed: {status['completed_steps']}")
    print(f"Failed: {status['failed_steps']}")

    # 6. Get Step Status
    print("\n6. Get Step Status")
    print("-" * 40)

    for step in result.steps:
        step_status = engine.get_step_status(workflow.id, step.id)
        print(f"  {step.name}: {step_status['status']}")

    # 7. Create Code Review Workflow (Template)
    print("\n7. Create Code Review Workflow (Template)")
    print("-" * 40)

    def dummy_handler(**kwargs):
        return {"status": "done"}

    for action in ["analyze_code", "check_style", "check_security", "generate_report"]:
        engine.register_handler(action, dummy_handler)

    review_workflow = create_code_review_workflow(engine)

    print(f"Workflow name: {review_workflow.name}")
    print(f"Steps: {len(review_workflow.steps)}")

    for step in review_workflow.steps:
        print(f"  - {step.name} ({step.action})")

    # 8. Create Data Pipeline Workflow (Template)
    print("\n8. Create Data Pipeline Workflow (Template)")
    print("-" * 40)

    for action in ["extract_data", "transform_data", "validate_data", "load_data"]:
        engine.register_handler(action, dummy_handler)

    pipeline_workflow = create_data_pipeline_workflow(engine)

    print(f"Workflow name: {pipeline_workflow.name}")
    print(f"Steps: {len(pipeline_workflow.steps)}")

    for step in pipeline_workflow.steps:
        deps = (
            f" (depends on: {', '.join(step.dependencies)})"
            if step.dependencies
            else ""
        )
        print(f"  - {step.name}{deps}")

    # 9. Export Workflow
    print("\n9. Export Workflow")
    print("-" * 40)

    exported = engine.export_workflow(workflow.id)

    print("Exported workflow (first 200 chars):")
    print(exported[:200] + "...")

    # 10. Import Workflow
    print("\n10. Import Workflow")
    print("-" * 40)

    imported = engine.import_workflow(exported)

    print(f"Imported workflow ID: {imported.id}")
    print(f"Imported workflow name: {imported.name}")

    # 11. List All Workflows
    print("\n11. List All Workflows")
    print("-" * 40)

    workflows = engine.list_workflows()

    print(f"Total workflows: {len(workflows)}")
    for wf in workflows:
        print(f"  - {wf.name} ({wf.id[:8]}...)")

    # 12. Clean Up
    print("\n12. Clean Up")
    print("-" * 40)

    for wf in workflows:
        engine.delete_workflow(wf.id)

    print(f"Remaining workflows: {len(engine.workflows)}")

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
