# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Performance benchmarks
- CI/CD with GitHub Actions
- Comprehensive CONTRIBUTING.md

## [0.7.0] - 2026-04-21

### Added
- **MCP (Model Context Protocol)**
  - Server implementation for Claude compatibility
  - Tools: router_call, memory_search, swarm_run, experience_get_advice
  - Resources: config/models, config/agents, memory/stats, experience/lessons
  - Prompts: code_generation, code_review, task_planning
  - Client for connecting to other MCP servers

- **RAG (Retrieval-Augmented Generation)**
  - Document storage and retrieval
  - Text chunking with overlap
  - Vector embeddings (hash-based)
  - Cosine similarity search
  - Context generation for RAG
  - Persistence to disk

- **Task Queue System**
  - Priority-based task queue
  - Worker threads for parallel processing
  - Task scheduler for future execution
  - Recurring tasks support
  - Task retry with max retries

- **Examples**
  - MCP Server example (07_mcp_server.py)
  - RAG System example (08_rag_system.py)

### Changed
- Updated version to 0.7.0
- Added MCP exports to __init__.py
- Added RAG exports to __init__.py
- Added TaskQueue exports to __init__.py

## [0.6.0] - 2026-04-21

### Added
- **Web Search** (inspired by OpenClaude)
  - DuckDuckGo integration (free)
  - HTML-to-markdown conversion
  - Search and fetch APIs
  - CLI command: `swarm search "query"`
  - CLI command: `swarm fetch "url"`

- **Provider Profiles** (inspired by OpenClaude)
  - Multi-provider support (OpenAI, Gemini, DeepSeek, Ollama, Groq, Mistral)
  - Provider profiles with saved configurations
  - Agent routing to different models
  - CLI command: `swarm providers`
  - CLI command: `swarm routing`

- **Streaming System** (inspired by OpenClaude)
  - Real-time token output
  - Stream manager with state management
  - Token counter with statistics
  - Progress tracker for long operations
  - Rate limiter for API calls

- **Hooks System** (inspired by OpenClaude)
  - Lifecycle hooks for agents, tools, memory, experience
  - Hook priority and execution order
  - Hook statistics and tracking
  - Decorator for easy hook registration
  - Builder pattern for fluent API

- **Tool System** (inspired by OpenClaude)
  - Bash tool for command execution
  - Read tool for file reading
  - Write tool for file writing
  - Edit tool for file editing
  - Grep tool for file searching
  - Glob tool for file finding
  - Tool registry for management

- **Examples**
  - Basic usage example
  - Web search example
  - Provider management example
  - Streaming example
  - Hooks example
  - Tools example

### Changed
- Updated models.yaml to use qwen2.5:7b and phi4:14b
- Fixed Unicode characters for Windows compatibility in CLI
- Added 6 new examples
- Added 6 new test files (197+ tests total)

## [0.5.0] - 2026-04-21

### Added
- **Multi-tier Memory System**
  - Working Memory (short-term, Miller's law 7±2)
  - Episodic Memory (events and experiences)
  - Semantic Memory (compressed knowledge)
  - Automatic memory compression
  - Memory promotion between tiers
  
- **Plugin System**
  - Plugin discovery and loading
  - Hot-swap plugins
  - Lifecycle hooks (on_load, on_unload, etc.)
  - Plugin configuration
  - Template creation

- **Integration Tests**
  - End-to-end testing
  - 9 comprehensive integration tests
  - All 85 tests passing

### Changed
- Improved memory search performance
- Fixed episodic memory search bug
- Updated documentation

## [0.4.0] - 2026-04-21

### Added
- **Web Dashboard**
  - FastAPI backend
  - Real-time status monitoring
  - Memory/Experience/Swarm stats
  - Run tasks from web UI
  - CLI command: `swarm dashboard`

### Changed
- Updated README with dashboard commands
- Added FastAPI and uvicorn dependencies

## [0.3.0] - 2026-04-21

### Added
- **Anonymizer** for PII protection
  - Detect: emails, IPs, phones, API keys, passwords, SSNs, credit cards
  - Anonymize: Replace PII with tokens
  - Restore: De-anonymize LLM responses
  - Custom patterns support
  - 16 new tests for Anonymizer

### Changed
- Updated `__init__.py` to export Anonymizer components
- Added CLI command: `swarm anonymize`

## [0.2.0] - 2026-04-21

### Added
- **Memory System**
  - Persistent storage for agent interactions
  - Search by agent, task, or content
  - Export/import memories
  - Stats and cleanup

- **Experience System**
  - Self-improvement from past experiences
  - Track successes and failures
  - Extract patterns and lessons
  - Best practices and warnings per task type
  - Confidence scoring

- **Swarm Intelligence**
  - Task decomposition
  - Agent assignment based on capabilities
  - Parallel execution with dependencies
  - Result aggregation

### Changed
- Updated CLI with new commands
- Added tests for all new components
- 32 tests passing (16 + 16)

## [0.1.0] - 2026-04-21

### Added
- **Initial Release**
  - Router: Universal LLM routing with auto-detection
  - Orchestrator: Multi-agent coordination
  - 4 Agents: Planner, Coder, Reviewer, Researcher
  - CLI: Full command-line interface
  - 100% Local with Ollama
  - Arabic support
  - 16 tests passing

### Inspiration
- Inspired by openclaude, ai-orchestrator, dario, LLM-anonymization, clawcode, obsidian-llm-wiki-local

---

## Version History

| Version | Date | Key Features |
|---------|------|--------------|
| 0.5.0 | 2026-04-21 | Multi-tier Memory, Plugin System, Integration Tests |
| 0.4.0 | 2026-04-21 | Web Dashboard, FastAPI |
| 0.3.0 | 2026-04-21 | Anonymizer, PII Protection |
| 0.2.0 | 2026-04-21 | Memory, Experience, Swarm |
| 0.1.0 | 2026-04-21 | Initial Release |

---

## Roadmap

### Completed
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
- [x] CI/CD - GitHub Actions
- [x] Contributing Guide

### Planned
- [ ] Performance Benchmarks
- [ ] Real-time Collaboration
- [ ] Voice Interface
- [ ] Mobile Dashboard
- [ ] Plugin Marketplace
- [ ] Video Tutorials
- [ ] Contribution Examples

---

## Contributors

- **Mohamed Elsaeed** - *Initial work* - [dvhma1994](https://github.com/dvhma1994)

See also the list of [contributors](https://github.com/dvhma1994/openclaw-swarm/graphs/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Inspired by:
- [openclaude](https://github.com/Gitlawb/openclaude) - 22K stars
- [ai-orchestrator](https://github.com/Mybono/ai-orchestrator) - Multi-agent Bash
- [dario](https://github.com/askalf/dario) - Universal LLM router
- [engram](https://github.com/emipanelliok/engram) - Persistent memory
- [prax-agent](https://github.com/ChanningLua/prax-agent) - Self-improving agent
- [ClawSwarm](https://github.com/1Panel-dev/ClawSwarm) - Swarm intelligence
- [open-multi-agent](https://github.com/JackChen-me/open-multi-agent) - 5K+ stars
- [kiwiq](https://github.com/rcortx/kiwiq) - 1K+ stars
- [LLM-anonymization](https://github.com/zeroc00I/LLM-anonymization) - Privacy-first