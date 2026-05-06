"""
Multi-Agent Swarm Orchestration - Inspired by MassGen + Claude Squad.
Coordinates multiple agents working in parallel on tasks with:
- Redundant execution for quality via consensus voting
- Real-time collaboration via shared state
- Convergence detection for efficiency
- Adaptive coordination based on task complexity
"""

from .orchestrator import SwarmOrchestrator

__all__ = ["SwarmOrchestrator"]
