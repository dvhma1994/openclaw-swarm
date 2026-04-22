"""
Skills Marketplace
==================
Inspired by: Antigravity Awesome Skills (1400+ installable skills),
             VoltAgent/awesome-agent-skills, alirezarevani/claude-skills.

A searchable, installable catalog of skills that extend OpenClaw.
Skills are SKILL.md playbooks that can be:
- Searched by category, risk level, keyword
- Installed to local skill directories
- Bundled into role-based workflows
- Shared across agents (Claude Code, Cursor, Codex, Gemini CLI)

Categories: development, testing, security, infrastructure, content,
            trading, monitoring, memory, debugging, devops
"""

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(
    os.environ.get(
        "OPENCLAW_DIRECTOR_DIR", Path.home() / ".openclaw" / "workspaces" / "director"
    )
)
SKILLS_DIR = BASE_DIR / "skills_marketplace"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)
REGISTRY_FILE = SKILLS_DIR / "skill_registry.json"
INSTALLED_DIR = SKILLS_DIR / "installed"


class SkillRisk(str, Enum):
    SAFE = "safe"  # Read-only, no shell, no network
    LOW = "low"  # Limited shell, no destructive ops
    MEDIUM = "medium"  # Full shell, file writes
    HIGH = "high"  # Network access, deployments
    NONE = "none"  # No restriction


class SkillCategory(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"
    CONTENT = "content"
    TRADING = "trading"
    MONITORING = "monitoring"
    MEMORY = "memory"
    DEBUGGING = "debugging"
    DEVOPS = "devops"
    ANALYSIS = "analysis"
    COMMUNICATION = "communication"


@dataclass
class SkillEntry:
    """A skill in the marketplace."""

    skill_id: str
    name: str
    description: str
    category: SkillCategory = SkillCategory.DEVELOPMENT
    risk: SkillRisk = SkillRisk.SAFE
    version: str = "1.0.0"
    author: str = ""
    tags: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)  # Other skill_ids
    content: str = ""  # The SKILL.md content
    source: str = "local"  # local, github, community
    source_url: str = ""
    installs: int = 0
    rating: float = 0.0
    compatible_tools: list = field(
        default_factory=list
    )  # ["claude", "cursor", "codex"]
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self):
        return {
            **asdict(self),
            "category": self.category.value,
            "risk": self.risk.value,
        }

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        data["category"] = SkillCategory(data.get("category", "development"))
        data["risk"] = SkillRisk(data.get("risk", "safe"))
        return cls(**data)


class SkillsMarketplace:
    """
    Manages the skill catalog: search, install, create, bundle.
    """

    def __init__(self, registry_file: Path = REGISTRY_FILE):
        self.registry_file = registry_file
        self.skills: Dict[str, SkillEntry] = {}
        self.installed_dir = INSTALLED_DIR
        self.installed_dir.mkdir(parents=True, exist_ok=True)
        self._load()
        # Register built-in skills if registry empty
        if not self.skills:
            self._register_builtin_skills()

    def _load(self):
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for s in data.get("skills", []):
                    skill = SkillEntry.from_dict(s)
                    self.skills[skill.skill_id] = skill
            except Exception:
                pass

    def _save(self):
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(self.registry_file.parent), suffix=".tmp"
        )
        try:
            data = {
                "skills": [s.to_dict() for s in self.skills.values()],
                "count": len(self.skills),
                "updated": datetime.now(timezone.utc).isoformat(),
            }
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            os.replace(tmp_path, str(self.registry_file))
        except Exception:
            os.unlink(tmp_path)
            raise

    def _register_builtin_skills(self):
        """Register core skills from the existing skill_contract system."""
        builtins = [
            SkillEntry(
                skill_id="brainstorming",
                name="Brainstorming",
                description="Plan features, MVPs, and product ideas using structured ideation",
                category=SkillCategory.DEVELOPMENT,
                risk=SkillRisk.SAFE,
                tags=["planning", "ideation", "product"],
                content="# Brainstorming\n\nUse this skill to plan features and generate ideas.\n\n1. Define the problem\n2. Generate 10+ ideas\n3. Score each idea (impact, effort, risk)\n4. Pick top 3\n5. Create action plan",
                compatible_tools=["claude", "cursor", "codex", "gemini"],
            ),
            SkillEntry(
                skill_id="code-review",
                name="Code Review",
                description="Automated code review focusing on quality, security, and best practices",
                category=SkillCategory.TESTING,
                risk=SkillRisk.SAFE,
                tags=["review", "quality", "security"],
                content="# Code Review\n\n1. Check syntax (AST parse)\n2. Check imports\n3. Security scan (40+ patterns)\n4. Type safety\n5. Error handling\n6. Complexity check\n7. Style consistency",
                compatible_tools=["claude", "cursor", "codex"],
            ),
            SkillEntry(
                skill_id="security-audit",
                name="Security Audit",
                description="Full security audit: input sanitization, secret scanning, dependency check",
                category=SkillCategory.SECURITY,
                risk=SkillRisk.SAFE,
                tags=["security", "audit", "secrets", "vulnerabilities"],
                content="# Security Audit\n\n1. Secret scanning (API keys, passwords, tokens)\n2. Input sanitization check\n3. Dependency vulnerability scan\n4. Permission review\n5. Network exposure check",
                compatible_tools=["claude", "codex"],
            ),
            SkillEntry(
                skill_id="bug-hunter",
                name="Bug Hunter",
                description="Find and fix bugs using systematic debugging with evolution engine",
                category=SkillCategory.DEBUGGING,
                risk=SkillRisk.MEDIUM,
                tags=["debugging", "bugs", "auto-fix"],
                content="# Bug Hunter\n\n1. Reproduce the bug\n2. Identify root cause\n3. Generate fix candidates\n4. Test each candidate\n5. Promote best fix\n6. Verify no regression",
                compatible_tools=["claude", "cursor"],
            ),
            SkillEntry(
                skill_id="architect",
                name="Architecture Review",
                description="Analyze system architecture, identify bottlenecks, suggest improvements",
                category=SkillCategory.DEVELOPMENT,
                risk=SkillRisk.SAFE,
                tags=["architecture", "design", "review"],
                content="# Architecture Review\n\n1. Map dependencies\n2. Identify tight coupling\n3. Check error handling patterns\n4. Evaluate scaling bottlenecks\n5. Score: cohesion, coupling, complexity\n6. Propose improvements",
                compatible_tools=["claude", "codex"],
            ),
            SkillEntry(
                skill_id="test-writer",
                name="Test Writer",
                description="Automatically write unit tests for any code module",
                category=SkillCategory.TESTING,
                risk=SkillRisk.LOW,
                tags=["testing", "unit-tests", "coverage"],
                content="# Test Writer\n\n1. Analyze public API of target module\n2. Generate test cases for each function\n3. Include edge cases and error paths\n4. Run tests to verify\n5. Report coverage",
                compatible_tools=["claude", "cursor", "codex"],
            ),
            SkillEntry(
                skill_id="deployer",
                name="Deployer",
                description="Safe deployment with rollback capability and health checks",
                category=SkillCategory.DEVOPS,
                risk=SkillRisk.HIGH,
                tags=["deployment", "rollback", "ci/cd"],
                content="# Deployer\n\n1. Run pre-deploy checks\n2. Create rollback snapshot\n3. Deploy with canary strategy\n4. Monitor health metrics\n5. Auto-rollback if degradation detected",
                compatible_tools=["claude"],
            ),
            SkillEntry(
                skill_id="doc-writer",
                name="Documentation Writer",
                description="Generate comprehensive documentation for code, APIs, and configs",
                category=SkillCategory.CONTENT,
                risk=SkillRisk.SAFE,
                tags=["docs", "documentation", "readme"],
                content="# Documentation Writer\n\n1. Analyze code structure\n2. Extract public API\n3. Generate README.md\n4. Generate API docs\n5. Add usage examples\n6. Create CHANGELOG.md",
                compatible_tools=["claude", "cursor", "codex", "gemini"],
            ),
            SkillEntry(
                skill_id="perf-profiler",
                name="Performance Profiler",
                description="Profile code performance and identify optimization opportunities",
                category=SkillCategory.DEBUGGING,
                risk=SkillRisk.MEDIUM,
                tags=["performance", "profiling", "optimization"],
                content="# Performance Profiler\n\n1. Identify hot paths\n2. Measure function timing\n3. Find memory allocations\n4. Detect N+1 queries\n5. Propose optimizations\n6. Verify improvement",
                compatible_tools=["claude"],
            ),
            SkillEntry(
                skill_id="memory-curator",
                name="Memory Curator",
                description="Manage and consolidate the dual-layer memory system",
                category=SkillCategory.MEMORY,
                risk=SkillRisk.SAFE,
                tags=["memory", "consolidation", "knowledge"],
                content="# Memory Curator\n\n1. Run consolidation (auto -> conscious)\n2. Clean stale entries\n3. Update knowledge graph\n4. Verify recall accuracy\n5. Report memory stats",
                compatible_tools=["claude"],
            ),
            SkillEntry(
                skill_id="trading-analyzer",
                name="Trading Analyzer",
                description="Analyze market data with technical and SMC features",
                category=SkillCategory.TRADING,
                risk=SkillRisk.HIGH,
                tags=["trading", "market", "xauusd", "technical"],
                content="# Trading Analyzer\n\n1. Fetch latest market data\n2. Calculate technical indicators\n3. Apply SMC features\n4. Generate signal\n5. Constitutional check\n6. Execute if approved",
                compatible_tools=["claude"],
            ),
            SkillEntry(
                skill_id="monitor",
                name="System Monitor",
                description="Real-time system monitoring with drift detection and alerting",
                category=SkillCategory.MONITORING,
                risk=SkillRisk.SAFE,
                tags=["monitoring", "health", "drift", "alerts"],
                content="# System Monitor\n\n1. Check all services\n2. Measure latencies\n3. Detect drift\n4. Check budget usage\n5. Generate alerts if needed",
                compatible_tools=["claude"],
            ),
        ]
        for skill in builtins:
            self.skills[skill.skill_id] = skill
        self._save()

    def publish(
        self,
        name: str,
        description: str,
        content: str,
        category: str = "development",
        risk: str = "safe",
        tags: list = None,
        author: str = "",
        compatible_tools: list = None,
    ) -> SkillEntry:
        """Publish a new skill to the marketplace."""
        skill_id = f"skill_{hashlib.md5(name.lower().encode()).hexdigest()[:8]}"
        skill = SkillEntry(
            skill_id=skill_id,
            name=name,
            description=description,
            category=SkillCategory(category),
            risk=SkillRisk(risk),
            content=content,
            tags=tags or [],
            author=author,
            compatible_tools=compatible_tools or ["claude"],
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self.skills[skill_id] = skill
        self._save()
        return skill

    def install(self, skill_id: str, target_dir: Path = None) -> dict:
        """Install a skill to the local skill directory."""
        if skill_id not in self.skills:
            return {"success": False, "error": f"Skill '{skill_id}' not found"}
        skill = self.skills[skill_id]
        target = target_dir or self.installed_dir
        target.mkdir(parents=True, exist_ok=True)
        skill_file = target / f"{skill_id}.md"
        with open(skill_file, "w", encoding="utf-8") as f:
            f.write(skill.content)
        skill.installs += 1
        self._save()
        return {
            "success": True,
            "installed_to": str(skill_file),
            "skill": skill.name,
            "version": skill.version,
        }

    def install_bundle(self, bundle_category: str, target_dir: Path = None) -> dict:
        """Install all skills in a category."""
        skills = self.search_by_category(bundle_category)
        results = {"installed": 0, "failed": 0, "details": []}
        for skill in skills:
            result = self.install(skill.skill_id, target_dir)
            if result["success"]:
                results["installed"] += 1
            else:
                results["failed"] += 1
            results["details"].append(result)
        return results

    def search(
        self,
        query: str = "",
        category: str = "",
        risk: str = "",
        tag: str = "",
        compatible_tool: str = "",
    ) -> List[SkillEntry]:
        """Search the skill catalog."""
        results = list(self.skills.values())
        if category:
            results = [s for s in results if s.category.value == category]
        if risk:
            results = [s for s in results if s.risk.value == risk]
        if tag:
            results = [s for s in results if tag in s.tags]
        if compatible_tool:
            results = [s for s in results if compatible_tool in s.compatible_tools]
        if query:
            ql = query.lower()
            scored = []
            for s in results:
                score = 0
                if ql in s.name.lower():
                    score += 3
                if ql in s.description.lower():
                    score += 2
                if any(ql in t.lower() for t in s.tags):
                    score += 1
                if score > 0:
                    scored.append((s, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            results = [s for s, _ in scored]
        return results

    def search_by_category(self, category: str) -> List[SkillEntry]:
        return [s for s in self.skills.values() if s.category.value == category]

    def get(self, skill_id: str) -> Optional[SkillEntry]:
        return self.skills.get(skill_id)

    def list_categories(self) -> dict:
        """List all categories with count."""
        cats = {}
        for s in self.skills.values():
            cat = s.category.value
            cats[cat] = cats.get(cat, 0) + 1
        return cats

    def get_stats(self) -> dict:
        return {
            "total_skills": len(self.skills),
            "categories": self.list_categories(),
            "total_installs": sum(s.installs for s in self.skills.values()),
            "by_risk": {
                r: sum(1 for s in self.skills.values() if s.risk.value == r)
                for r in set(s.risk.value for s in self.skills.values())
            },
        }


_marketplace: Optional[SkillsMarketplace] = None


def get_marketplace() -> SkillsMarketplace:
    global _marketplace
    if _marketplace is None:
        _marketplace = SkillsMarketplace()
    return _marketplace


if __name__ == "__main__":
    import sys

    mp = get_marketplace()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        print(json.dumps(mp.get_stats(), indent=2))
    elif cmd == "search":
        results = mp.search(
            query=sys.argv[2] if len(sys.argv) > 2 else "",
            category=sys.argv[3] if len(sys.argv) > 3 else "",
        )
        for s in results:
            print(f"  [{s.category.value:15s}] {s.name}: {s.description[:60]}")
    elif cmd == "categories":
        print(json.dumps(mp.list_categories(), indent=2))
    elif cmd == "install" and len(sys.argv) > 2:
        result = mp.install(sys.argv[2])
        print(json.dumps(result, indent=2))
    elif cmd == "install-bundle" and len(sys.argv) > 2:
        result = mp.install_bundle(sys.argv[2])
        print(json.dumps(result, indent=2))
    else:
        print(
            "Commands: stats, search [query] [category], categories, install <id>, install-bundle <category>"
        )
