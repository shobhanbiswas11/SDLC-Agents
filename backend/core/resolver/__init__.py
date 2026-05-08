"""
Resolution engine for dependency conflicts
Provides strategies, backtracking, and orchestration
"""

from .strategies import ResolutionStrategy, MinimalChangeStrategy, LatestVersionStrategy
from .engine import ResolutionEngine, resolve_conflicts

__all__ = [
    "ResolutionStrategy",
    "MinimalChangeStrategy",
    "LatestVersionStrategy",
    "ResolutionEngine",
    "resolve_conflicts"
]
