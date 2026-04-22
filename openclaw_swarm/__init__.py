"""OpenClaw Swarm - Multi-Agent AI System"""

__version__ = "0.7.0"
__author__ = "Mohamed Elsaeed"

from .agents import Coder, Planner, Researcher, Reviewer
from .anonymizer import Anonymizer, PIIEntity, anonymize, check_pii, de_anonymize
from .evaluation import (
    Benchmark,
    EvaluationResult,
    Evaluator,
    MetricResult,
    MetricType,
    create_cost_benchmark,
    create_performance_benchmark,
    create_quality_benchmark,
)
from .experience import Experience, ExperienceDB, Lesson, get_advice, learn
from .hooks import Hook, HookContext, HookManager, HookResult, HookType
from .mcp import (
    MCPClient,
    MCPPrompt,
    MCPResource,
    MCPServer,
    MCPTool,
    create_mcp_server,
)
from .memory import Memory, MemoryEntry, recall, remember
from .multi_tier_memory import (
    EpisodicMemory,
    MultiTierMemory,
    SemanticMemory,
    WorkingMemory,
    create_memory_system,
)
from .orchestrator import Orchestrator
from .plugins import PluginManager, PluginType, create_plugin_manager
from .providers import AgentRouter, ProviderManager, ProviderProfile, ProviderType
from .rag import (
    Chunk,
    Document,
    RAGSystem,
    SearchResult,
    SimpleEmbedder,
    TextChunker,
    VectorStore,
)
from .router import Router, TaskType
from .streaming import (
    ProgressTracker,
    RateLimiter,
    StreamGenerator,
    StreamManager,
    TokenCounter,
)
from .swarm import (
    AgentRole,
    SwarmAgent,
    SwarmCoordinator,
    SwarmTask,
)
from .swarm import TaskPriority as SwarmTaskPriority
from .swarm import (
    run_swarm,
)
from .task_queue import (
    Task,
    TaskPriority,
    TaskQueue,
    TaskScheduler,
    TaskStatus,
    Worker,
)
from .tools import (
    BashTool,
    EditTool,
    GlobTool,
    GrepTool,
    ReadTool,
    Tool,
    ToolRegistry,
    ToolResult,
    ToolType,
    WriteTool,
)
from .web_search import SearchResult as WebSearchResult
from .web_search import WebSearch
from .workflow import (
    ConditionType,
    StepStatus,
    Workflow,
    WorkflowEngine,
    WorkflowStatus,
    WorkflowStep,
    create_code_review_workflow,
    create_data_pipeline_workflow,
)

__all__ = [
    "Router",
    "TaskType",
    "Orchestrator",
    "Memory",
    "MemoryEntry",
    "remember",
    "recall",
    "ExperienceDB",
    "Experience",
    "Lesson",
    "learn",
    "get_advice",
    "Anonymizer",
    "PIIEntity",
    "anonymize",
    "de_anonymize",
    "check_pii",
    "MultiTierMemory",
    "WorkingMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "create_memory_system",
    "PluginManager",
    "PluginType",
    "create_plugin_manager",
    "SwarmCoordinator",
    "SwarmAgent",
    "SwarmTask",
    "AgentRole",
    "TaskPriority",
    "run_swarm",
    "Planner",
    "Coder",
    "Reviewer",
    "Researcher",
    "WebSearch",
    "SearchResult",
    "ProviderManager",
    "ProviderProfile",
    "ProviderType",
    "AgentRouter",
    "StreamManager",
    "StreamGenerator",
    "TokenCounter",
    "ProgressTracker",
    "RateLimiter",
    "HookManager",
    "Hook",
    "HookType",
    "HookContext",
    "HookResult",
    "ToolRegistry",
    "Tool",
    "ToolType",
    "ToolResult",
    "BashTool",
    "ReadTool",
    "WriteTool",
    "EditTool",
    "GrepTool",
    "GlobTool",
    "MCPServer",
    "MCPClient",
    "MCPTool",
    "MCPResource",
    "MCPPrompt",
    "create_mcp_server",
    "RAGSystem",
    "Document",
    "Chunk",
    "SearchResult",
    "WebSearchResult",
    "TextChunker",
    "SimpleEmbedder",
    "VectorStore",
    "TaskQueue",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "SwarmTaskPriority",
    "TaskScheduler",
    "Worker",
    "WorkflowEngine",
    "Workflow",
    "WorkflowStep",
    "WorkflowStatus",
    "StepStatus",
    "ConditionType",
    "create_code_review_workflow",
    "create_data_pipeline_workflow",
    "Evaluator",
    "Benchmark",
    "MetricResult",
    "EvaluationResult",
    "MetricType",
    "create_performance_benchmark",
    "create_quality_benchmark",
    "create_cost_benchmark",
]
