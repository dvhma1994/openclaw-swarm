# Contributing to OpenClaw Swarm

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## 🌟 Ways to Contribute

### 1. Report Bugs
- Check if the bug has already been reported in [Issues](https://github.com/dvhma1994/openclaw-swarm/issues)
- If not, create a new issue with:
  - Clear title and description
  - Steps to reproduce
  - Expected vs actual behavior
  - Python version and OS
  - Error messages and logs

### 2. Suggest Features
- Open an issue with the label "enhancement"
- Describe the feature and its use case
- Explain how it fits with the project

### 3. Submit Code
- Fork the repository
- Create a feature branch
- Make your changes
- Submit a pull request

### 4. Improve Documentation
- Fix typos and errors
- Add examples and tutorials
- Improve API documentation

### 5. Add Tests
- Write unit tests for new features
- Improve test coverage
- Add integration tests

## 🔧 Development Setup

### Prerequisites
- Python 3.10 or higher
- Git
- Ollama (for local testing)

### Setup Steps

```bash
# Clone the repository
git clone https://github.com/dvhma1994/openclaw-swarm.git
cd openclaw-swarm

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install test dependencies
pip install pytest pytest-cov pytest-benchmark

# Run tests
pytest tests/ -v
```

## 📝 Code Style

### Python
- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://github.com/psf/black) for formatting
- Use [isort](https://pycqa.github.io/isort/) for imports
- Use [Ruff](https://github.com/astral-sh/ruff) for linting

### Type Hints
- Use type hints for all public functions
- Use `Optional` for optional parameters
- Use `List`, `Dict`, etc. from `typing`

### Docstrings
- Use Google-style docstrings
- Include parameter types and return types
- Add examples for complex functions

```python
def example_function(param1: str, param2: int = 0) -> Dict[str, Any]:
    """Short description.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1.
        param2: Description of param2. Defaults to 0.
    
    Returns:
        Description of return value.
    
    Raises:
        ValueError: If param1 is empty.
    
    Example:
        >>> result = example_function("test", 42)
        >>> print(result)
    """
    pass
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_router.py -v

# Run with coverage
pytest tests/ --cov=openclaw_swarm --cov-report=html

# Run benchmarks
pytest tests/test_performance.py --benchmark-only
```

### Write Tests
- Use `pytest` framework
- Test file names should start with `test_`
- Test class names should start with `Test`
- Test function names should start with `test_`

```python
import pytest

class TestExample:
    def test_something(self):
        # Arrange
        obj = SomeClass()
        
        # Act
        result = obj.do_something()
        
        # Assert
        assert result == expected_value
```

## 📋 Pull Request Process

1. **Fork and Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write clean, documented code
   - Add tests for new features
   - Update documentation

3. **Run Checks**
   ```bash
   # Format code
   black openclaw_swarm tests
   isort openclaw_swarm tests
   
   # Lint
   ruff check openclaw_swarm tests
   
   # Test
   pytest tests/ -v
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```
   
   Use conventional commits:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `test:` for tests
   - `refactor:` for code refactoring
   - `perf:` for performance improvements

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   
   Then create a Pull Request on GitHub.

6. **PR Description**
   - Clear title and description
   - Link related issues
   - List breaking changes
   - Add screenshots if applicable

## 🏗️ Project Structure

```
openclaw-swarm/
├── openclaw_swarm/          # Main package
│   ├── __init__.py
│   ├── router.py            # LLM routing
│   ├── orchestrator.py      # Agent coordination
│   ├── memory.py            # Persistent memory
│   ├── experience.py        # Experience learning
│   ├── anonymizer.py        # PII protection
│   ├── swarm.py             # Swarm coordination
│   ├── multi_tier_memory.py # Working/Episodic/Semantic
│   ├── plugins.py           # Plugin system
│   ├── dashboard.py         # Web UI
│   └── agents/              # Agent implementations
│       ├── planner.py
│       ├── coder.py
│       ├── reviewer.py
│       └── researcher.py
├── tests/                   # Test files
├── config/                  # Configuration files
│   ├── agents.yaml
│   └── models.yaml
├── docs/                    # Documentation
├── examples/                # Usage examples
├── pyproject.toml           # Package config
├── requirements.txt         # Dependencies
├── README.md                # Main documentation
├── EXAMPLES.md              # Code examples
├── CONTRIBUTING.md          # This file
└── LICENSE                  # MIT License
```

## 📦 Adding New Features

### Add a New Agent

1. Create agent file in `openclaw_swarm/agents/`:

```python
# openclaw_swarm/agents/my_agent.py
from ..router import Router, TaskType

class MyAgent:
    """My custom agent"""
    
    SYSTEM_PROMPT = """You are a helpful agent..."""
    
    def __init__(self):
        self.router = Router()
        self.name = "MyAgent"
        self.model_type = TaskType.GENERAL
    
    def execute(self, task: str) -> str:
        # Implementation
        pass
```

2. Add to `openclaw_swarm/agents/__init__.py`

3. Add tests in `tests/test_my_agent.py`

### Add a New Plugin

1. Create plugin directory:
```bash
swarm plugins create my_plugin
```

2. Edit `plugins/my_plugin/main.py`

3. Add hooks:
```python
def on_load(config):
    print("Plugin loaded!")

def before_request(request):
    return request
```

### Add a New Router Model

1. Edit `config/models.yaml`:
```yaml
models:
  new_task:
    primary: "model-name"
    fallback: "backup-model"
    timeout: 120
```

## 🐛 Reporting Issues

### Security Issues
- Do NOT open public issues for security vulnerabilities
- Email security issues to: security@example.com

### Bug Reports
Include:
- Python version
- OS and version
- OpenClaw Swarm version
- Minimal reproducible example
- Error traceback

## 📖 Documentation

### API Documentation
- Document all public functions
- Include parameter types
- Add usage examples

### README Updates
- Keep examples up to date
- Document new features
- Update roadmap

## 🎯 Code Review Checklist

PRs are reviewed for:
- [ ] Code style and formatting
- [ ] Test coverage
- [ ] Documentation
- [ ] Performance considerations
- [ ] Security concerns
- [ ] Backward compatibility

## 💬 Getting Help

- Open an issue for bugs
- Start a discussion for features
- Join our community (link coming soon)

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to OpenClaw Swarm! 🦀