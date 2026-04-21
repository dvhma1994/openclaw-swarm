# OpenClaw Swarm - Examples

## Quick Examples

### 1. Basic Usage

```python
from openclaw_swarm import run_swarm

# Run a simple task
result = run_swarm("Create a Python function to sort a list")
print(result["final_result"])
```

### 2. Use Router Directly

```python
from openclaw_swarm import Router, TaskType

router = Router()

# Auto-detect task type
response = router.call("Write a Python function")
print(response)

# Specify task type
response = router.call("Debug this code", TaskType.CODING)
print(response)
```

### 3. Use Individual Agents

```python
from openclaw_swarm import Planner, Coder, Reviewer

planner = Planner()
coder = Coder()
reviewer = Reviewer()

# Plan a task
plan = planner.plan("Build a REST API")

# Generate code
code = coder.code("Create a FastAPI endpoint for users")

# Review code
review = reviewer.review(code)
print(review)
```

### 4. Memory System

```python
from openclaw_swarm import Memory

memory = Memory()

# Store experience
memory.store(
    agent="Coder",
    task="Create API",
    input_data="User requested REST API",
    output_data="FastAPI code",
    success=True
)

# Search memories
results = memory.find_similar("API")
print(results)

# Get stats
stats = memory.get_stats()
print(stats)
```

### 5. Experience Learning

```python
from openclaw_swarm import ExperienceDB

exp = ExperienceDB()

# Record experience
exp.record_experience(
    task_type="coding",
    context="REST API development",
    action_taken="Used FastAPI with Pydantic",
    result="Success - fast and clean",
    success=True
)

# Get advice
advice = exp.get_advice("coding")
print("Best practices:", advice["best_practices"])
print("Warnings:", advice["warnings"])
```

### 6. Multi-tier Memory

```python
from openclaw_swarm import MultiTierMemory

mtm = MultiTierMemory()

# Working memory (short-term)
mtm.add_to_working("Current task: Build API", priority=8)

# Episodic memory (events)
mtm.store_event(
    event="Completed API task",
    participants=["Coder", "Reviewer"],
    context="Building REST API",
    outcome="Success",
    importance=0.8,
    tags=["api", "coding"]
)

# Recall from all tiers
results = mtm.recall("API")
print(results)

# Get stats
stats = mtm.get_stats()
print(stats)
```

### 7. Anonymizer (PII Protection)

```python
from openclaw_swarm import Anonymizer

anon = Anonymizer()

# Detect PII
text = "Contact me at john@example.com or call 555-123-4567"
entities = anon.detect_pii(text)
print(f"Found {len(entities)} PII entities")

# Anonymize
result = anon.anonymize(text)
print(result.anonymized)
# Output: "Contact me at <PII_EMAIL_1> or call <PII_PHONE_1>"

# De-anonymize
original = anon.de_anonymize(result.anonymized, result.mapping)
print(original)
```

### 8. Swarm Coordination

```python
from openclaw_swarm import SwarmCoordinator

coordinator = SwarmCoordinator()

# Run complex task with decomposition
result = coordinator.run_swarm(
    "Build a complete REST API with authentication",
    max_workers=3,
    decompose=True
)

print(f"Completed {result['completed']}/{result['subtasks']} subtasks")
print(result["final_result"])

# Get status
status = coordinator.get_status()
print(f"Agents: {len(status['agents'])}")
print(f"Memory: {status['memory_stats']['total_memories']}")
```

### 9. Plugin System

```python
from openclaw_swarm import PluginManager

pm = PluginManager()

# Create a plugin template
pm.create_plugin_template("my_custom_agent", "agent")

# Load plugin
pm.load_plugin("my_custom_agent")

# List plugins
plugins = pm.list_plugins()
for plugin in plugins:
    print(f"{plugin.name} v{plugin.version}")

# Get stats
stats = pm.get_stats()
print(f"Total plugins: {stats['total_plugins']}")
```

### 10. Orchestrator Workflow

```python
from openclaw_swarm import Orchestrator

orch = Orchestrator()

# Run default workflow
results = orch.run_workflow(
    "Create a Python script that reads a CSV and generates a report"
)

# Custom workflow
results = orch.run_workflow(
    "Review this code",
    workflow=["reviewer"]
)

# Run in parallel
results = orch.run_parallel(
    "Generate documentation",
    agents=["researcher", "coder"]
)
```

### 11. Dashboard

```python
from openclaw_swarm.dashboard import run_server

# Launch dashboard
run_server(host="0.0.0.0", port=8000)
# Open http://localhost:8000/dashboard
```

### 12. CLI Usage

```bash
# Run task
swarm run "Create a Python function"

# Chat
swarm chat "Hello!"

# Plan
swarm plan "Build a REST API"

# Code
swarm code "Create a FastAPI endpoint"

# Review
swarm review mycode.py

# Memory stats
swarm memory stats

# Experience advice
swarm experience advice --task coding

# Swarm coordination
swarm swarm "Build complete application"

# Anonymize
swarm anonymize "My email is test@example.com"

# Launch dashboard
swarm dashboard --port 8000
```

## Integration Examples

### 13. With OpenClaude

```python
from openclaw_swarm import SwarmCoordinator
import subprocess

# Use OpenClaude for coding
def code_with_openclaude(prompt):
    result = subprocess.run(
        ["openclaude", "-p", prompt],
        capture_output=True,
        text=True
    )
    return result.stdout

# Integrate with Swarm
coordinator = SwarmCoordinator()
# ... use OpenClaude as a backend
```

### 14. With Ollama Directly

```python
import ollama
from openclaw_swarm import Router

# Direct Ollama call
response = ollama.chat(
    model="gemma3:27b",
    messages=[{"role": "user", "content": "Hello"}]
)

# Or use Router
router = Router()
response = router.call("Hello")  # Auto-routes to best model
```

### 15. Async Usage

```python
import asyncio
from openclaw_swarm import SwarmCoordinator

async def run_tasks():
    coordinator = SwarmCoordinator()
    
    # Run multiple tasks concurrently
    tasks = [
        coordinator.run_swarm("Task 1"),
        coordinator.run_swarm("Task 2"),
        coordinator.run_swarm("Task 3"),
    ]
    
    results = await asyncio.gather(*tasks)
    return results

# Run
results = asyncio.run(run_tasks())
```

## Advanced Examples

### 16. Custom Agent

```python
from openclaw_swarm import Orchestrator, Router, TaskType

class CustomAgent:
    def __init__(self, name, specialty):
        self.name = name
        self.specialty = specialty
        self.router = Router()
    
    def execute(self, task):
        prompt = f"You are {self.name}, specialized in {self.specialty}.\n\nTask: {task}"
        return self.router.call(prompt, TaskType.GENERAL)

# Use custom agent
analyst = CustomAgent("Analyst", "data analysis")
result = analyst.execute("Analyze this dataset")
```

### 17. Memory Pipeline

```python
from openclaw_swarm import MultiTierMemory

mtm = MultiTierMemory()

# Store in working memory
mtm.add_to_working("Analyze data", priority=9)

# Process...
# Promote to episodic when important
mtm.promote_working_to_episodic("item_id")

# Compress to semantic periodically
mtm.run_compression()

# Query all tiers
recall = mtm.recall("data")
```

### 18. Plugin Development

```python
# In plugins/my_plugin/main.py

def on_load(config):
    """Called when plugin loads"""
    print(f"Loaded with config: {config}")

def before_request(request):
    """Middleware before request"""
    # Anonymize PII
    from openclaw_swarm import Anonymizer
    anon = Anonymizer()
    result = anon.anonymize(request)
    return result.anonymized

def after_request(response):
    """Middleware after request"""
    # De-anonymize
    # ...
    return response
```

## Real-World Use Cases

### 19. Code Review Pipeline

```python
from openclaw_swarm import Orchestrator

orch = Orchestrator()

# Custom review workflow
results = orch.run_workflow(
    "Review the codebase",
    workflow=["planner", "reviewer"]
)

for agent_id, result in results.items():
    print(f"{result.agent_name}: {result.output[:200]}")
```

### 20. Research Assistant

```python
from openclaw_swarm import Researcher, MultiTierMemory

researcher = Researcher()
memory = MultiTierMemory()

# Research and remember
topics = ["AI agents", "Multi-agent systems", "LLM orchestration"]

for topic in topics:
    result = researcher.research(topic)
    memory.store_event(
        event=f"Researched {topic}",
        participants=["Researcher"],
        context="Learning session",
        outcome=result,
        tags=["research", topic]
    )

# Recall later
recall = memory.recall("AI agents")
```

---

For more examples, see the `examples/` directory in the repository.