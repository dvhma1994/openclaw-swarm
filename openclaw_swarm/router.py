"""
Router - Universal LLM Router
Inspired by dario - Single endpoint, multiple providers
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import yaml
import ollama
from rich.console import Console

console = Console()


class TaskType(Enum):
    CODING = "coding"
    REASONING = "reasoning"
    CHAT = "chat"
    GENERAL = "general"
    ARABIC = "arabic"


@dataclass
class ModelConfig:
    primary: str
    fallback: str
    timeout: int


class Router:
    """Universal LLM Router - Routes to best model for each task"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), "..", "config", "models.yaml"
        )
        self.config = self._load_config()
        self.models = self._parse_models()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration from YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            console.print(f"[yellow]Config not found at {self.config_path}, using defaults[/yellow]")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration if file not found"""
        return {
            "models": {
                "coding": {"primary": "qwen2.5:14b", "fallback": "qwen2.5:7b", "timeout": 120},
                "reasoning": {"primary": "phi4:14b", "fallback": "gemma3:12b", "timeout": 180},
                "chat": {"primary": "gemma3:27b", "fallback": "glm-5:cloud", "timeout": 60},
                "general": {"primary": "glm-5:cloud", "fallback": "gemma3:12b", "timeout": 90},
                "arabic": {"primary": "gemma3:27b", "fallback": "glm-5:cloud", "timeout": 90},
            },
            "ollama": {"base_url": "http://localhost:11434", "timeout": 300}
        }
    
    def _parse_models(self) -> Dict[TaskType, ModelConfig]:
        """Parse model configurations"""
        models = {}
        for task_type in TaskType:
            if task_type.value in self.config.get("models", {}):
                cfg = self.config["models"][task_type.value]
                models[task_type] = ModelConfig(
                    primary=cfg["primary"],
                    fallback=cfg["fallback"],
                    timeout=cfg["timeout"]
                )
        return models
    
    def detect_task_type(self, prompt: str) -> TaskType:
        """Auto-detect task type from prompt content"""
        prompt_lower = prompt.lower()
        
        # Arabic detection
        arabic_chars = sum(1 for c in prompt if '\u0600' <= c <= '\u06FF')
        if arabic_chars > len(prompt) * 0.2:
            return TaskType.ARABIC
        
        # Coding keywords
        coding_keywords = ['code', 'function', 'class', 'script', 'python', 'javascript', 
                          'implement', 'debug', 'fix', 'error', 'api', 'module']
        if any(kw in prompt_lower for kw in coding_keywords):
            return TaskType.CODING
        
        # Reasoning keywords
        reasoning_keywords = ['why', 'explain', 'analyze', 'compare', 'evaluate',
                             'reason', 'think', 'logic', 'solve']
        if any(kw in prompt_lower for kw in reasoning_keywords):
            return TaskType.REASONING
        
        # Chat keywords
        chat_keywords = ['hello', 'hi', 'how are', 'chat', 'talk', 'conversation']
        if any(kw in prompt_lower for kw in chat_keywords):
            return TaskType.CHAT
        
        return TaskType.GENERAL
    
    def get_model(self, task_type: TaskType) -> str:
        """Get primary model for task type"""
        return self.models.get(task_type, self.models[TaskType.GENERAL]).primary
    
    def get_fallback_model(self, task_type: TaskType) -> str:
        """Get fallback model for task type"""
        return self.models.get(task_type, self.models[TaskType.GENERAL]).fallback
    
    def call(
        self, 
        prompt: str, 
        task_type: Optional[TaskType] = None,
        model: Optional[str] = None,
        stream: bool = False
    ) -> str:
        """
        Call LLM with automatic routing
        
        Args:
            prompt: The prompt to send
            task_type: Optional task type (auto-detected if None)
            model: Optional specific model (overrides routing)
            stream: Whether to stream the response
            
        Returns:
            Model response as string
        """
        # Detect task type if not provided
        if task_type is None:
            task_type = self.detect_task_type(prompt)
        
        # Use specified model or route to best model
        model_name = model or self.get_model(task_type)
        
        console.print(f"[dim]Using model: {model_name} (task: {task_type.value})[/dim]")
        
        try:
            if stream:
                return self._call_stream(model_name, prompt)
            else:
                return self._call_sync(model_name, prompt, task_type)
        except Exception as e:
            console.print(f"[red]Error with {model_name}: {e}[/red]")
            # Try fallback
            fallback = self.get_fallback_model(task_type)
            if fallback != model_name:
                console.print(f"[yellow]Trying fallback: {fallback}[/yellow]")
                return self._call_sync(fallback, prompt, task_type)
            raise
    
    def _call_sync(self, model: str, prompt: str, task_type: TaskType) -> str:
        """Synchronous call to Ollama"""
        response = ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}]
        )
        return response['message']['content']
    
    def _call_stream(self, model: str, prompt: str) -> str:
        """Stream response from Ollama"""
        full_response = ""
        for chunk in ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            stream=True
        ):
            content = chunk['message']['content']
            full_response += content
            console.print(content, end='')
        console.print()  # Newline after streaming
        return full_response


# Convenience function
def route(prompt: str, task_type: Optional[TaskType] = None) -> str:
    """Quick route to best model"""
    router = Router()
    return router.call(prompt, task_type)