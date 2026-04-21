"""OpenClaw Swarm - Multi-Agent AI System"""

__version__ = "0.5.0"
__author__ = "Mohamed Elsaeed"

from .router import Router, TaskType
from .orchestrator import Orchestrator
from .memory import Memory, MemoryEntry, remember, recall
from .experience import ExperienceDB, Experience, Lesson, learn, get_advice
from .anonymizer import Anonymizer, PIIEntity, anonymize, de_anonymize, check_pii
from .multi_tier_memory import MultiTierMemory, WorkingMemory, EpisodicMemory, SemanticMemory, create_memory_system
from .plugins import PluginManager, PluginType, create_plugin_manager
from .swarm import SwarmCoordinator, SwarmAgent, SwarmTask, AgentRole, TaskPriority, run_swarm
from .agents import Planner, Coder, Reviewer, Researcher
from .web_search import WebSearch, SearchResult
from .providers import ProviderManager, ProviderProfile, ProviderType, AgentRouter
from .streaming import StreamManager, StreamGenerator, TokenCounter, ProgressTracker, RateLimiter
from .hooks import HookManager, Hook, HookType, HookContext, HookResult
from .tools import ToolRegistry, Tool, ToolType, ToolResult, BashTool, ReadTool, WriteTool, EditTool, GrepTool, GlobTool

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
]