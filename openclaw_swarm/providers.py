"""
OpenClaw Swarm - Provider Profiles
Manage multiple AI providers and models
"""

import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProviderType(Enum):
    """Supported provider types"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"
    GROQ = "groq"
    MISTRAL = "mistral"
    OPENROUTER = "openrouter"
    CUSTOM = "custom"


@dataclass
class ProviderProfile:
    """Provider configuration profile"""

    name: str
    provider_type: ProviderType
    base_url: str
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    models: List[str] = None
    capabilities: List[str] = None
    max_tokens: int = 4096
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False

    def __post_init__(self):
        if self.models is None:
            self.models = []
        if self.capabilities is None:
            self.capabilities = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["provider_type"] = self.provider_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderProfile":
        """Create from dictionary"""
        data["provider_type"] = ProviderType(data["provider_type"])
        return cls(**data)


class ProviderManager:
    """Manage provider profiles"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(
            config_path or "~/.openclaw-swarm/profiles.json"
        ).expanduser()
        self.profiles: Dict[str, ProviderProfile] = {}
        self.active_profile: Optional[str] = None
        self._load_profiles()

    def _load_profiles(self):
        """Load profiles from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    for name, profile_data in data.get("profiles", {}).items():
                        self.profiles[name] = ProviderProfile.from_dict(profile_data)
                    self.active_profile = data.get("active_profile")
            except Exception as e:
                print(f"Error loading profiles: {e}")

    def _save_profiles(self):
        """Save profiles to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "profiles": {name: p.to_dict() for name, p in self.profiles.items()},
            "active_profile": self.active_profile,
        }
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_profile(self, profile: ProviderProfile) -> bool:
        """Add a new provider profile"""
        self.profiles[profile.name] = profile
        self._save_profiles()
        return True

    def remove_profile(self, name: str) -> bool:
        """Remove a provider profile"""
        if name in self.profiles:
            del self.profiles[name]
            if self.active_profile == name:
                self.active_profile = None
            self._save_profiles()
            return True
        return False

    def get_profile(self, name: str) -> Optional[ProviderProfile]:
        """Get a provider profile"""
        return self.profiles.get(name)

    def set_active(self, name: str) -> bool:
        """Set active provider profile"""
        if name in self.profiles:
            self.active_profile = name
            self._save_profiles()
            return True
        return False

    def get_active(self) -> Optional[ProviderProfile]:
        """Get active provider profile"""
        if self.active_profile:
            return self.profiles.get(self.active_profile)
        return None

    def list_profiles(self) -> List[str]:
        """List all profile names"""
        return list(self.profiles.keys())

    def get_default_models(self) -> Dict[str, str]:
        """Get default models for all providers"""
        return {
            ProviderType.OPENAI: "gpt-4o",
            ProviderType.ANTHROPIC: "claude-3-5-sonnet-20241022",
            ProviderType.GEMINI: "gemini-2.0-flash",
            ProviderType.DEEPSEEK: "deepseek-chat",
            ProviderType.OLLAMA: "qwen2.5:7b",
            ProviderType.GROQ: "llama-3.3-70b-versatile",
            ProviderType.MISTRAL: "mistral-large-latest",
            ProviderType.OPENROUTER: "anthropic/claude-3.5-sonnet",
            ProviderType.CUSTOM: "",
        }

    def create_ollama_profile(self) -> ProviderProfile:
        """Create Ollama provider profile"""
        return ProviderProfile(
            name="ollama",
            provider_type=ProviderType.OLLAMA,
            base_url="http://localhost:11434/v1",
            default_model="qwen2.5:7b",
            models=["qwen2.5:7b", "phi4:14b", "glm-5:cloud"],
            capabilities=["chat", "completion", "streaming"],
            max_tokens=128000,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
        )

    def create_openai_profile(self, api_key: str) -> ProviderProfile:
        """Create OpenAI provider profile"""
        return ProviderProfile(
            name="openai",
            provider_type=ProviderType.OPENAI,
            base_url="https://api.openai.com/v1",
            api_key=api_key,
            default_model="gpt-4o",
            models=["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            capabilities=["chat", "completion", "streaming", "vision", "tools"],
            max_tokens=128000,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
        )

    def create_gemini_profile(self, api_key: str) -> ProviderProfile:
        """Create Gemini provider profile"""
        return ProviderProfile(
            name="gemini",
            provider_type=ProviderType.GEMINI,
            base_url="https://generativelanguage.googleapis.com/v1beta",
            api_key=api_key,
            default_model="gemini-2.0-flash",
            models=["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
            capabilities=["chat", "completion", "streaming", "vision"],
            max_tokens=1000000,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
        )

    def create_deepseek_profile(self, api_key: str) -> ProviderProfile:
        """Create DeepSeek provider profile"""
        return ProviderProfile(
            name="deepseek",
            provider_type=ProviderType.DEEPSEEK,
            base_url="https://api.deepseek.com/v1",
            api_key=api_key,
            default_model="deepseek-chat",
            models=["deepseek-chat", "deepseek-coder"],
            capabilities=["chat", "completion", "streaming", "tools"],
            max_tokens=64000,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
        )


class AgentRouter:
    """Route agents to specific providers/models"""

    def __init__(self):
        self.routing: Dict[str, str] = {}
        self.default_model: str = "qwen2.5:7b"

    def set_routing(self, agent_name: str, model: str):
        """Set model for specific agent"""
        self.routing[agent_name] = model

    def get_model(self, agent_name: str) -> str:
        """Get model for agent"""
        return self.routing.get(agent_name, self.default_model)

    def set_default(self, model: str):
        """Set default model"""
        self.default_model = model

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return {"default": self.default_model, "routing": self.routing}

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "AgentRouter":
        """Create from dictionary"""
        router = cls()
        router.default_model = data.get("default", "qwen2.5:7b")
        router.routing = data.get("routing", {})
        return router
