"""
OpenClaw Swarm CLI
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from .orchestrator import Orchestrator
from .router import Router, TaskType

app = typer.Typer(
    name="swarm",
    help="OpenClaw Swarm - Multi-Agent AI System",
    add_completion=False
)
console = Console()


@app.command()
def run(
    prompt: str = typer.Argument(..., help="The task or prompt to process"),
    workflow: str = typer.Option("default", "--workflow", "-w", help="Workflow to use"),
    parallel: bool = typer.Option(False, "--parallel", "-p", help="Run agents in parallel"),
    show_progress: bool = typer.Option(True, "--progress/--no-progress", help="Show progress"),
):
    """Run a multi-agent workflow on a prompt"""
    orchestrator = Orchestrator()
    
    console.print(Panel.fit(
        f"[bold blue]OpenClaw Swarm[/bold blue]\n[dim]Processing: {prompt[:50]}...[/dim]",
        border_style="blue"
    ))
    
    if parallel:
        console.print("[yellow]Running agents in parallel...[/yellow]")
        results = orchestrator.run_parallel(prompt)
    else:
        workflow_list = workflow.split(",") if "," in workflow else None
        results = orchestrator.run_workflow(prompt, workflow_list, show_progress)
    
    # Display results
    console.print("\n[bold green]═══ Results ═══[/bold green]\n")
    
    for agent_id, result in results.items():
        status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
        console.print(f"\n[bold]{status} {result.agent_name}[/bold] ({result.duration_ms}ms)")
        
        if result.success:
            console.print(Markdown(result.output[:500] + "..." if len(result.output) > 500 else result.output))
        else:
            console.print(f"[red]Error: {result.error}[/red]")


@app.command()
def agents():
    """List available agents"""
    orchestrator = Orchestrator()
    
    table = Table(title="Available Agents")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Role", style="yellow")
    table.add_column("Model Type", style="magenta")
    
    for agent_id, agent in orchestrator.agents.items():
        table.add_row(
            agent_id,
            agent.name,
            agent.role,
            agent.model_type
        )
    
    console.print(table)


@app.command()
def models():
    """List configured models"""
    router = Router()
    
    table = Table(title="Configured Models")
    table.add_column("Task Type", style="cyan")
    table.add_column("Primary Model", style="green")
    table.add_column("Fallback Model", style="yellow")
    
    for task_type in TaskType:
        model_config = router.models.get(task_type)
        if model_config:
            table.add_row(
                task_type.value,
                model_config.primary,
                model_config.fallback
            )
    
    console.print(table)


@app.command()
def chat(
    message: str = typer.Argument(..., help="Message to send"),
    model: str = typer.Option(None, "--model", "-m", help="Specific model to use"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream response"),
):
    """Quick chat with auto-routing"""
    router = Router()
    
    console.print("[dim]Routing to best model...[/dim]")
    
    response = router.call(message, model=model, stream=stream)
    
    if not stream:
        console.print(Markdown(response))


@app.command()
def code(
    task: str = typer.Argument(..., help="Coding task"),
    language: str = typer.Option("python", "--lang", "-l", help="Programming language"),
    fix: bool = typer.Option(False, "--fix", "-f", help="Fix mode (provide code and error)"),
):
    """Quick code generation/fix"""
    from .agents import Coder
    
    coder = Coder()
    
    if fix:
        # In fix mode, task should contain both code and error
        result = coder.fix("", task, language)
    else:
        result = coder.code(task, language)
    
    console.print(Markdown(result))


@app.command()
def review(
    code_file: str = typer.Argument(..., help="File containing code to review"),
    security: bool = typer.Option(False, "--security", "-s", help="Security audit mode"),
):
    """Review code for issues"""
    from .agents import Reviewer
    
    try:
        with open(code_file, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        console.print(f"[red]Error: File '{code_file}' not found[/red]")
        raise typer.Exit(1)
    
    reviewer = Reviewer()
    
    if security:
        result = reviewer.security_audit(code)
    else:
        result = reviewer.review(code)
    
    console.print(Markdown(result))


@app.command()
def plan(
    task: str = typer.Argument(..., help="Task to plan"),
):
    """Create a plan for a task"""
    from .agents import Planner
    
    planner = Planner()
    result = planner.plan(task)
    
    console.print(Markdown(result))


@app.command()
def version():
    """Show version information"""
    from . import __version__
    console.print(f"[bold blue]OpenClaw Swarm[/bold blue] version [green]{__version__}[/green]")


@app.command()
def memory(
    action: str = typer.Argument(..., help="Action: stats, clear, export"),
    filepath: str = typer.Option(None, "--file", "-f", help="File path for export/import"),
):
    """Manage agent memory"""
    from .memory import Memory
    
    mem = Memory()
    
    if action == "stats":
        stats = mem.get_stats()
        table = Table(title="Memory Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in stats.items():
            if isinstance(value, dict):
                table.add_row(key, f"{len(value)} items")
            else:
                table.add_row(key, str(value))
        
        console.print(table)
    
    elif action == "clear":
        count = mem.clear_old(days=0)
        console.print(f"[green]Cleared {count} memories[/green]")
    
    elif action == "export":
        if not filepath:
            filepath = "memories_export.json"
        mem.export(filepath)
    
    else:
        console.print(f"[red]Unknown action: {action}[/red]")


@app.command()
def experience(
    action: str = typer.Argument(..., help="Action: stats, advice, export"),
    task_type: str = typer.Option("general", "--task", "-t", help="Task type for advice"),
    filepath: str = typer.Option(None, "--file", "-f", help="File path for export"),
):
    """Manage experience database"""
    from .experience import ExperienceDB
    
    exp = ExperienceDB()
    
    if action == "stats":
        stats = exp.get_stats()
        table = Table(title="Experience Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in stats.items():
            if isinstance(value, list):
                table.add_row(key, f"{len(value)} types")
            else:
                table.add_row(key, str(value))
        
        console.print(table)
    
    elif action == "advice":
        advice = exp.get_advice(task_type)
        
        if advice["best_practices"]:
            console.print("[bold green]Best Practices:[/bold green]")
            for practice in advice["best_practices"]:
                console.print(f"  - {practice}")
        
        if advice["warnings"]:
            console.print("[bold yellow]Warnings:[/bold yellow]")
            for warning in advice["warnings"]:
                console.print(f"  - {warning}")
    
    elif action == "export":
        if not filepath:
            filepath = "rules_export.json"
        exp.export_rules(filepath)
    
    else:
        console.print(f"[red]Unknown action: {action}[/red]")


@app.command()
def swarm(
    task: str = typer.Argument(..., help="Task for the swarm"),
    decompose: bool = typer.Option(True, "--decompose/--no-decompose", help="Decompose complex tasks"),
    workers: int = typer.Option(3, "--workers", "-w", help="Max parallel workers"),
):
    """Run a swarm of agents on a task"""
    from .swarm import SwarmCoordinator
    
    console.print(Panel.fit(
        f"[bold blue]OpenClaw Swarm[/bold blue]\n[dim]Task: {task[:50]}...[/dim]",
        border_style="blue"
    ))
    
    coordinator = SwarmCoordinator()
    result = coordinator.run_swarm(task, max_workers=workers, decompose=decompose)
    
    console.print("\n[bold green]=== Final Result ===[/bold green]")
    console.print(Markdown(result["final_result"]))
    
    console.print(f"\n[dim]Completed {result['completed']}/{result['subtasks']} subtasks[/dim]")


@app.command()
def anonymize_cmd(
    text: str = typer.Argument(..., help="Text to anonymize"),
    types: str = typer.Option(None, "--types", "-t", help="PII types to anonymize (comma-separated)"),
):
    """Anonymize PII in text"""
    from .anonymizer import Anonymizer
    
    anon = Anonymizer()
    
    type_list = types.split(",") if types else None
    result = anon.anonymize(text, types=type_list)
    
    console.print("\n[bold green]Anonymized Text:[/bold green]")
    console.print(result.anonymized)
    
    console.print("\n[bold yellow]Detected PII:[/bold yellow]")
    for entity in result.entities:
        console.print(f"  - {entity.type}: {entity.value[:20]}...")
    
    console.print(f"\n[dim]Replaced {len(result.entities)} PII entities[/dim]")


@app.command()
def dashboard(
    port: int = typer.Option(8000, "--port", "-p", help="Dashboard port"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Dashboard host"),
):
    """Launch web dashboard"""
    from .dashboard import run_server
    
    console.print(Panel.fit(
        f"[bold blue]OpenClaw Swarm Dashboard[/bold blue]\n[dim]http://{host}:{port}/dashboard[/dim]",
        border_style="blue"
    ))
    
    console.print("\n[yellow]Press Ctrl+C to stop[/yellow]")
    
    try:
        run_server(host=host, port=port)
    except KeyboardInterrupt:
        console.print("\n[green]Dashboard stopped[/green]")


if __name__ == "__main__":
    app()