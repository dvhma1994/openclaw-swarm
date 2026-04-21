# OpenClaw Swarm 🦀

**Multi-Agent AI System - 100% Local with Ollama**

A hybrid multi-agent system combining the best ideas from top open-source projects:

- 🔄 **Router** (inspired by `dario`) - Universal LLM routing
- 🤖 **Orchestrator** (inspired by `ai-orchestrator`) - Multi-agent coordination
- 🧠 **Memory** (inspired by `obsidian-llm-wiki-local`) - Knowledge management
- 🔒 **Anonymizer** (inspired by `LLM-anonymization`) - Privacy-first
- 📈 **Learning** (inspired by `clawcode`) - Experience-based evolution

## Features

✅ 100% Local - No API keys required
✅ Multi-Agent - Planner, Coder, Reviewer, Researcher
✅ Smart Routing - Uses best model for each task
✅ Privacy-First - Anonymizes sensitive data
✅ Experience DB - Learns from mistakes
✅ Arabic Support - Works with Arabic prompts

## Models Used

| Task | Model | Why |
|------|-------|-----|
| Coding | Qwen 2.5 | Great at code |
| Reasoning | Phi4:14b | Logic tasks |
| Chat | Gemma3:27b | Conversations |
| General | GLM-5 | All-purpose |

## Quick Start

```bash
# Install
pip install openclaw-swarm

# Or from source
git clone https://github.com/dvhma1994/openclaw-swarm
cd openclaw-swarm
pip install -e .

# Run
swarm "Create a Python script that..."
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenClaw Swarm                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Router    │  │ Orchestrator│  │   Memory    │         │
│  │             │  │             │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Anonymizer  │  │  Auto-Pilot │  │ SEO Monitor │         │
│  │             │  │             │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────────────────────────────────────────┐       │
│  │              Ollama Backend                      │       │
│  │    Gemma3:27b | Phi4:14b | Qwen | GLM-5         │       │
│  └─────────────────────────────────────────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Router (from `dario`)
Universal LLM router - single endpoint, multiple providers.

### 2. Orchestrator (from `ai-orchestrator`)
Multi-agent coordination with role-based execution.

### 3. Memory (from `obsidian-llm-wiki-local`)
Knowledge management with auto-linking concepts.

### 4. Anonymizer (from `LLM-anonymization`)
Privacy-first PII tokenization.

### 5. Experience (from `clawcode`)
Learning from mistakes for better decisions.

## License

MIT

## Credits

Inspired by:
- [openclaude](https://github.com/Gitlawb/openclaude)
- [ai-orchestrator](https://github.com/Mybono/ai-orchestrator)
- [dario](https://github.com/askalf/dario)
- [LLM-anonymization](https://github.com/zeroc00I/LLM-anonymization)
- [clawcode](https://github.com/deepelementlab/clawcode)
- [obsidian-llm-wiki-local](https://github.com/kytmanov/obsidian-llm-wiki-local)