# OpenClaw Swarm

**Multi-Agent AI System - 100% Local with Ollama**

A hybrid multi-agent system combining the best ideas from top open-source projects:

- **Router** (inspired by `dario`) - Universal LLM routing
- **Orchestrator** (inspired by `ai-orchestrator`) - Multi-agent coordination
- **Memory** (inspired by `engram`, `obsidian-llm-wiki-local`) - Persistent memory
- **Experience** (inspired by `prax-agent`, `reflexion-agent-ts`) - Self-improvement
- **Swarm** (inspired by `ClawSwarm`, `open-multi-agent`) - Emergent intelligence

## Features

- **100% Local** - No API keys required
- **Multi-Agent** - Planner, Coder, Reviewer, Researcher
- **Smart Routing** - Uses best model for each task
- **Persistent Memory** - Remember past interactions
- **Experience Learning** - Learn from successes and failures
- **Swarm Intelligence** - Emergent coordination
- **Arabic Support** - Works with Arabic prompts

## Models Used

| Task | Model | Why |
|------|-------|-----|
| Coding | Qwen 2.5 | Great at code |
| Reasoning | Phi4:14b | Logic tasks |
| Chat | Gemma3:27b | Conversations |
| General | GLM-5 | All-purpose |

## Installation

```bash
# Install
pip install openclaw-swarm

# Or from source
git clone https://github.com/dvhma1994/openclaw-swarm
cd openclaw-swarm
pip install -e .
```

## Quick Start

```bash
# Run a task with swarm
swarm run "Create a Python function to sort a list"

# Chat with auto-routing
swarm chat "Hello, what can you do?"

# Plan a task
swarm plan "Build a REST API"

# Review code
swarm review mycode.py

# Run swarm coordination
swarm swarm "Build a complete web application"
```

## Commands

| Command | Description |
|---------|-------------|
| `swarm run "task"` | Run multi-agent workflow |
| `swarm chat "message"` | Quick chat with auto-routing |
| `swarm code "task"` | Code generation |
| `swarm plan "task"` | Task planning |
| `swarm review file.py` | Code review |
| `swarm agents` | List available agents |
| `swarm models` | List configured models |
| `swarm memory stats` | Memory statistics |
| `swarm experience advice` | Get learned advice |
| `swarm swarm "task"` | Run swarm coordination |
| `swarm dashboard` | Launch web UI |

## Architecture

```
+---------------------+-------------------------+
|          OpenClaw Swarm                       |
+---------------------+-------------------------+
|                                                 |
|  +----------+  +-------------+  +----------+  |
|  |  Router  |  | Orchestrator|  |  Memory  |  |
|  +----------+  +-------------+  +----------+  |
|                                                 |
|  +-----------+  +------------+  +-----------+  |
|  | Experience|  |    Swarm   |  |  Agents   |  |
|  +-----------+  +------------+  +-----------+  |
|                                                 |
|  +-----------------------------------------+   |
|  |            Ollama Backend               |   |
|  |   Gemma3:27b | Phi4:14b | Qwen | GLM-5 |   |
|  +-----------------------------------------+   |
|                                                 |
+---------------------+-------------------------+
```

## Components

### 1. Router (from `dario`)
Universal LLM router - single endpoint, multiple providers.

### 2. Orchestrator (from `ai-orchestrator`)
Multi-agent coordination with role-based execution.

### 3. Memory (from `engram`)
Persistent memory - remember past interactions.

### 4. Experience (from `prax-agent`)
Learn from mistakes for better decisions.

### 5. Swarm (from `ClawSwarm`)
Swarm intelligence - emergent coordination.

## Programmatic Usage

```python
from openclaw_swarm import SwarmCoordinator, Memory, ExperienceDB

# Initialize
swarm = SwarmCoordinator()
memory = Memory()
experience = ExperienceDB()

# Run a task
result = swarm.run_swarm("Create a Python REST API")
print(result["final_result"])

# Store memory
memory.store(
    agent="Coder",
    task="Create API",
    input_data="request",
    output_data="code",
    success=True
)

# Learn from experience
experience.record_experience(
    task_type="coding",
    context="REST API",
    action_taken="Used FastAPI",
    result="Success",
    success=True
)

# Get advice
advice = experience.get_advice("coding")
print(advice["best_practices"])
```

## Roadmap

- [x] Router - Universal LLM routing
- [x] Orchestrator - Multi-agent coordination
- [x] Memory - Persistent storage
- [x] Experience - Learning from mistakes
- [x] Swarm - Emergent intelligence
- [x] Anonymizer - Privacy-first PII protection
- [x] Multi-tier Memory - Working + Episodic + Semantic
- [x] Plugin System - Easy extensions
- [x] Web UI - Dashboard for monitoring
- [x] Integration Tests - End-to-end testing
- [ ] Performance Benchmarks
- [ ] Real-time Collaboration

## Stats

- Version: 0.5.0
- Tests: 95+ passing
- Files: 40+
- Lines: 20,000+
- Commits: 16
- Contributors: 1
- License: MIT

## License

MIT

## Credits

Inspired by:
- [openclaude](https://github.com/Gitlawb/openclaude) - 22K stars
- [ai-orchestrator](https://github.com/Mybono/ai-orchestrator) - Multi-agent Bash
- [dario](https://github.com/askalf/dario) - Universal LLM router
- [engram](https://github.com/emipanelliok/engram) - Persistent memory
- [prax-agent](https://github.com/ChanningLua/prax-agent) - Self-improving agent
- [ClawSwarm](https://github.com/1Panel-dev/ClawSwarm) - Swarm intelligence
- [open-multi-agent](https://github.com/JackChen-me/open-multi-agent) - 5K+ stars
- [kiwiq](https://github.com/rcortx/kiwiq) - 1K+ stars