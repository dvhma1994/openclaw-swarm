"""
Tests for Provider Profiles functionality
"""

import pytest
import tempfile
import json
from pathlib import Path

from openclaw_swarm.providers import (
    ProviderType,
    ProviderProfile,
    ProviderManager,
    AgentRouter,
)


class TestProviderType:
    """Test ProviderType enum"""

    def test_provider_types_exist(self):
        """Test all provider types exist"""
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.ANTHROPIC.value == "anthropic"
        assert ProviderType.GEMINI.value == "gemini"
        assert ProviderType.DEEPSEEK.value == "deepseek"
        assert ProviderType.OLLAMA.value == "ollama"
        assert ProviderType.GROQ.value == "groq"
        assert ProviderType.MISTRAL.value == "mistral"
        assert ProviderType.OPENROUTER.value == "openrouter"
        assert ProviderType.CUSTOM.value == "custom"


class TestProviderProfile:
    """Test ProviderProfile dataclass"""

    def test_profile_creation(self):
        """Test creating a provider profile"""
        profile = ProviderProfile(
            name="test",
            provider_type=ProviderType.OPENAI,
            base_url="https://api.openai.com/v1",
            api_key="test_key",
            default_model="gpt-4o",
        )

        assert profile.name == "test"
        assert profile.provider_type == ProviderType.OPENAI
        assert profile.base_url == "https://api.openai.com/v1"
        assert profile.api_key == "test_key"
        assert profile.default_model == "gpt-4o"

    def test_profile_defaults(self):
        """Test profile default values"""
        profile = ProviderProfile(
            name="test",
            provider_type=ProviderType.OLLAMA,
            base_url="http://localhost:11434/v1",
        )

        assert profile.models == []
        assert profile.capabilities == []
        assert profile.max_tokens == 4096
        assert profile.supports_streaming is True
        assert profile.supports_tools is True
        assert profile.supports_vision is False

    def test_profile_to_dict(self):
        """Test converting profile to dictionary"""
        profile = ProviderProfile(
            name="test",
            provider_type=ProviderType.OPENAI,
            base_url="https://api.openai.com/v1",
            default_model="gpt-4o",
            models=["gpt-4o", "gpt-3.5-turbo"],
        )

        data = profile.to_dict()

        assert data["name"] == "test"
        assert data["provider_type"] == "openai"
        assert data["base_url"] == "https://api.openai.com/v1"
        assert "gpt-4o" in data["models"]

    def test_profile_from_dict(self):
        """Test creating profile from dictionary"""
        data = {
            "name": "test",
            "provider_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "test_key",
            "default_model": "gpt-4o",
            "models": ["gpt-4o"],
            "capabilities": ["chat"],
            "max_tokens": 8192,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": False,
        }

        profile = ProviderProfile.from_dict(data)

        assert profile.name == "test"
        assert profile.provider_type == ProviderType.OPENAI
        assert profile.api_key == "test_key"


class TestProviderManager:
    """Test ProviderManager class"""

    def test_manager_initialization(self):
        """Test manager initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profiles.json"
            manager = ProviderManager(str(config_path))

            assert manager.profiles == {}
            assert manager.active_profile is None

    def test_add_profile(self):
        """Test adding a profile"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profiles.json"
            manager = ProviderManager(str(config_path))

            profile = ProviderProfile(
                name="test",
                provider_type=ProviderType.OPENAI,
                base_url="https://api.openai.com/v1",
            )

            result = manager.add_profile(profile)

            assert result is True
            assert "test" in manager.profiles

    def test_remove_profile(self):
        """Test removing a profile"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profiles.json"
            manager = ProviderManager(str(config_path))

            profile = ProviderProfile(
                name="test",
                provider_type=ProviderType.OPENAI,
                base_url="https://api.openai.com/v1",
            )

            manager.add_profile(profile)
            result = manager.remove_profile("test")

            assert result is True
            assert "test" not in manager.profiles

    def test_set_active_profile(self):
        """Test setting active profile"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profiles.json"
            manager = ProviderManager(str(config_path))

            profile = ProviderProfile(
                name="test",
                provider_type=ProviderType.OPENAI,
                base_url="https://api.openai.com/v1",
            )

            manager.add_profile(profile)
            result = manager.set_active("test")

            assert result is True
            assert manager.active_profile == "test"

    def test_get_active_profile(self):
        """Test getting active profile"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profiles.json"
            manager = ProviderManager(str(config_path))

            profile = ProviderProfile(
                name="test",
                provider_type=ProviderType.OPENAI,
                base_url="https://api.openai.com/v1",
            )

            manager.add_profile(profile)
            manager.set_active("test")

            active = manager.get_active()

            assert active is not None
            assert active.name == "test"

    def test_list_profiles(self):
        """Test listing profiles"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profiles.json"
            manager = ProviderManager(str(config_path))

            profile1 = ProviderProfile(
                name="test1",
                provider_type=ProviderType.OPENAI,
                base_url="https://api.openai.com/v1",
            )
            profile2 = ProviderProfile(
                name="test2",
                provider_type=ProviderType.GEMINI,
                base_url="https://generativelanguage.googleapis.com/v1beta",
            )

            manager.add_profile(profile1)
            manager.add_profile(profile2)

            profiles = manager.list_profiles()

            assert len(profiles) == 2
            assert "test1" in profiles
            assert "test2" in profiles

    def test_create_ollama_profile(self):
        """Test creating Ollama profile"""
        manager = ProviderManager()
        profile = manager.create_ollama_profile()

        assert profile.name == "ollama"
        assert profile.provider_type == ProviderType.OLLAMA
        assert "qwen2.5:7b" in profile.models

    def test_create_openai_profile(self):
        """Test creating OpenAI profile"""
        manager = ProviderManager()
        profile = manager.create_openai_profile("test_key")

        assert profile.name == "openai"
        assert profile.provider_type == ProviderType.OPENAI
        assert profile.api_key == "test_key"
        assert "gpt-4o" in profile.models

    def test_create_gemini_profile(self):
        """Test creating Gemini profile"""
        manager = ProviderManager()
        profile = manager.create_gemini_profile("test_key")

        assert profile.name == "gemini"
        assert profile.provider_type == ProviderType.GEMINI
        assert profile.api_key == "test_key"
        assert "gemini-2.0-flash" in profile.models

    def test_create_deepseek_profile(self):
        """Test creating DeepSeek profile"""
        manager = ProviderManager()
        profile = manager.create_deepseek_profile("test_key")

        assert profile.name == "deepseek"
        assert profile.provider_type == ProviderType.DEEPSEEK
        assert profile.api_key == "test_key"
        assert "deepseek-chat" in profile.models


class TestAgentRouter:
    """Test AgentRouter class"""

    def test_router_initialization(self):
        """Test router initialization"""
        router = AgentRouter()

        assert router.routing == {}
        assert router.default_model == "qwen2.5:7b"

    def test_set_routing(self):
        """Test setting routing"""
        router = AgentRouter()

        router.set_routing("planner", "phi4:14b")
        router.set_routing("coder", "qwen2.5:7b")

        assert router.routing["planner"] == "phi4:14b"
        assert router.routing["coder"] == "qwen2.5:7b"

    def test_get_model(self):
        """Test getting model for agent"""
        router = AgentRouter()

        router.set_routing("planner", "phi4:14b")

        assert router.get_model("planner") == "phi4:14b"
        assert router.get_model("unknown") == "qwen2.5:7b"

    def test_set_default(self):
        """Test setting default model"""
        router = AgentRouter()

        router.set_default("gpt-4o")

        assert router.default_model == "gpt-4o"

    def test_to_dict(self):
        """Test converting to dictionary"""
        router = AgentRouter()
        router.set_routing("planner", "phi4:14b")
        router.set_default("qwen2.5:7b")

        data = router.to_dict()

        assert data["default"] == "qwen2.5:7b"
        assert data["routing"]["planner"] == "phi4:14b"

    def test_from_dict(self):
        """Test creating from dictionary"""
        data = {
            "default": "gpt-4o",
            "routing": {"planner": "phi4:14b", "coder": "qwen2.5:7b"},
        }

        router = AgentRouter.from_dict(data)

        assert router.default_model == "gpt-4o"
        assert router.routing["planner"] == "phi4:14b"
        assert router.routing["coder"] == "qwen2.5:7b"
