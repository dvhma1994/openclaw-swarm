# OpenClaw v2 Supercharged - Changelog

## [2.0.0] - 2026-04-22

### New Systems (7 Major Features)

#### 1. Evolution Engine (evolution_engine/)
- **PatternDetector**: Scans failure logs to identify repeating error patterns
- **MutationGenerator**: Generates candidate improvements (code fixes, config tunes, prompt refinements)
- **FitnessEvaluator**: Evaluates mutations via AST syntax check, import validation, JSON schema check
- **SelectionController**: Selects best candidates for promotion (threshold-based)
- **RollbackManager**: Creates snapshots before mutations, restores on failure
- **EvolutionEngine**: Full orchestration: detect -> mutate -> evaluate -> select -> promote/rollback
- Inspired by: OpenAlpha_Evolve, Skynet Agent, MassGen, Plandex

#### 2. Swarm Orchestrator (swarm_orchestrator/)
- **SwarmAgent**: Agents with roles (coder, reviewer, planner, debugger, researcher) and reputation scoring
- **CollaborationHub**: Real-time shared state for inter-agent collaboration
- **ConsensusVoter**: 4 voting strategies (majority, best_score, consensus, weighted)
- **SwarmOrchestrator**: Parallel task execution with ThreadPoolExecutor
- Reputation-based agent selection with automatic trust boosting
- Inspired by: MassGen, Claude Squad, Plandex

#### 3. Dual-Layer Memory (dual_memory/)
- **AutomaticMemory**: Background RAG with TF-IDF-like retrieval
- **ConsciousMemory**: Deliberate, tagged, importance-scored (1-10) memories
- **KnowledgeGraph**: Entity-relationship mapping with BFS pathfinding
- **DualMemorySystem**: Unified interface: remember, recall, consolidate, learn_relationship
- Auto-consolidation from automatic to conscious memory
- Inspired by: Skynet Agent, Blade Code

#### 4. Credential Pool (credential_pool/)
- **Credential**: API key with health tracking, cooldown, daily limits
- **ProviderPool**: Per-provider credential management with priority & round-robin
- **CredentialPool**: Cross-provider failover with automatic rotation
- Handles: 429 (rate limit -> cooldown), 401/403 (invalid), 402 (exhausted)
- Exponential backoff on rate limits
- Daily reset and health monitoring
- Inspired by: OpenClaude Issue #780

#### 5. Auto-Heal Pipeline (auto_heal/)
- **LintChecker**: AST syntax + ruff/flake8 integration
- **TestRunner**: pytest with failure capture
- **AutoFixer**: Common fixes for syntax, unused imports, trailing whitespace
- **SelfHealPipeline**: lint -> fix -> re-lint loop (max 3 attempts)
- Integration with Evolution Engine for pattern learning
- Inspired by: Plandex, Kilocode, Cline

#### 6. Real-time HUD (realtime_hud/)
- **HUDMetrics**: 50+ metrics across all systems
- **Terminal rendering**: 2-3 line status (like Claude HUD)
- **HTML dashboard**: Full stats with auto-refresh (30s)
- **JSON API**: Programmatic access
- Collects from: Evolution, Swarm, Memory, Credentials, Git
- Inspired by: Claude HUD, MassGen TUI

#### 7. Skills Marketplace (skills_marketplace/)
- **12 built-in skills** across 9 categories
- Searchable catalog (query, category, risk, tag, compatibility)
- Install to local directories, bundle by category
- Risk classification (safe, low, medium, high)
- Compatible tool tracking (Claude, Cursor, Codex, Gemini)
- Inspired by: Antigravity Awesome Skills, VoltAgent

### Enhanced Systems (2 Major Upgrades)

#### 8. Constitutional Guardian v2 (constitutional_guardian_v2.py)
- **DriftDetector**: Monitors error rate, cost trends with 5-level severity
- **ReputationTracker**: Agent trust levels with compliance rate tracking
- **BudgetGuardian**: Daily (0) and weekly (0) hard budget limits
- **ConstitutionalGuardianV2**: Pre/post checks wired to all v2 systems
- Auto-heal trigger on critical drift
- Budget-based action blocking

#### 9. Headless/CI Mode (headless_mode/)
- **HeadlessRunner**: Full agent loop without interactive UI
- Permission modes: yolo, autoEdit, plan
- Output formats: text, json, stream-json, jsonl
- Constitutional pre-check integration
- Batch task execution
- Inspired by: Blade Code, Kilocode

### Unified Integration (openclaw_v2_core.py)
- **OpenClawV2**: Single entry point wiring ALL 11 systems
- Full execution pipeline: guardian -> memory -> execute -> heal -> audit -> memory -> HUD
- 11ms startup time for full pipeline
- Compatible with all existing OpenClaw modules

### Stats
- **New code**: ~3,500 lines across 9 files
- **New tests**: All modules importable and runnable
- **Systems online**: 11 (7 new + 4 existing)
- **Skills registered**: 12 (9 categories)
- **Agents ready**: 3 (director + qa + expert)

### Inspired By (Projects Studied)
| Project | Stars | Key Insight Adopted |
|---------|-------|-------------------|
| Cline | 60k | Checkpoint/rollback, browser automation |
| Pi Mono | 38k | Monorepo agent toolkit, TUI library |
| Antigravity Skills | 34k | 1400+ installable skills catalog |
| Claude HUD | 20k | Real-time statusline with context bar |
| Kilocode | 18k | Auto mode, multi-mode architecture |
| Plandex | 15k | Automated debugging, diff sandbox |
| MassGen | 1k | Consensus voting, parallel agents |
| Skynet Agent | 131 | Dual-layer memory, LangGraph autopilot |
| Blade Code | 959 | Headless mode, Web UI, memory system |
| OpenAlpha Evolve | 999 | Evolutionary code improvement cycles |
