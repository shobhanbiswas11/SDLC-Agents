"""
Main resolution engine
Orchestrates strategies and backtracking to resolve dependencies
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from .strategies import HybridStrategy, ResolutionStrategy
from .backtracker import backtrack_solve
from core.conflict_detector import detect_conflicts

logger = logging.getLogger(__name__)


class ResolutionEngine:
    """
    Main engine for resolving dependency conflicts

    Uses a hybrid approach:
    1. Try strategy-based resolution (fast, heuristic)
    2. If that fails, use backtracking (slower but thorough)
    3. Support human-in-the-loop for ambiguous cases
    """

    def __init__(
        self,
        registry_npm=None,
        registry_pypi=None,
        strategy: Optional[ResolutionStrategy] = None,
        max_strategy_iterations: int = 10,
        max_backtrack_iterations: int = 100
    ):
        """
        Initialize resolution engine

        Args:
            registry_npm: NPM registry client
            registry_pypi: PyPI registry client
            strategy: Resolution strategy to use (defaults to HybridStrategy)
            max_strategy_iterations: Max iterations for strategy
            max_backtrack_iterations: Max iterations for backtracking
        """
        self.registry_npm = registry_npm
        self.registry_pypi = registry_pypi
        self.strategy = strategy or HybridStrategy(registry_npm, registry_pypi)
        self.max_strategy_iterations = max_strategy_iterations
        self.max_backtrack_iterations = max_backtrack_iterations
        self.resolution_history: List[Dict[str, Any]] = []

    async def resolve(
        self,
        dependency_graph: Dict[str, Any],
        file_type: str,
        auto_resolve: bool = True
    ) -> Tuple[Dict[str, str], List[Dict[str, Any]], bool]:
        """
        Attempt to resolve all conflicts in dependency graph

        Args:
            dependency_graph: Full dependency graph
            file_type: 'package.json' or 'requirements.txt'
            auto_resolve: If False, ask for human input on ambiguous cases

        Returns:
            Tuple of (resolved_versions, remaining_conflicts, success)
        """
        self.resolution_history = []

        # Get initial resolution from graph
        current_resolution = {
            pkg: info.get("selected_version", "*")
            for pkg, info in dependency_graph.items()
            if info.get("selected_version")
        }

        logger.info(f"Starting resolution with {len(current_resolution)} packages")

        # Phase 1: Strategy-based resolution
        logger.info("[Phase 1] Using strategy-based resolution")
        resolved, history = await self._strategy_phase(
            dependency_graph,
            current_resolution,
            file_type
        )

        self.resolution_history.extend(history)

        # Check if resolved
        conflicts = detect_conflicts(dependency_graph)
        if not conflicts:
            logger.info("✓ Resolution successful!")
            return resolved, [], True

        logger.warning(f"Strategy phase failed, {len(conflicts)} conflicts remain")

        # Phase 2: Backtracking
        if len(conflicts) > 0:
            logger.info("[Phase 2] Using backtracking solver")
            resolved, backtrack_iterations = await backtrack_solve(
                dependency_graph,
                resolved,
                file_type,
                self.registry_npm,
                self.registry_pypi,
                self.max_backtrack_iterations
            )

            self.resolution_history.append({
                "phase": "backtracking",
                "iterations": backtrack_iterations,
                "success": resolved is not None
            })

            if resolved:
                logger.info("✓ Backtracking succeeded!")
                # Update graph with resolved versions
                for pkg, version in resolved.items():
                    if pkg in dependency_graph:
                        dependency_graph[pkg]["selected_version"] = version

                conflicts = detect_conflicts(dependency_graph)
                return resolved, [], not bool(conflicts)

        # Phase 3: Human-in-the-loop (if enabled and still conflicts)
        if not auto_resolve and conflicts:
            logger.info("[Phase 3] Awaiting human input")
            # Human input would be handled by agent
            return resolved, conflicts, False

        logger.warning("Failed to resolve conflicts")
        return resolved, conflicts, False

    async def _strategy_phase(
        self,
        dependency_graph: Dict[str, Any],
        current_resolution: Dict[str, str],
        file_type: str
    ) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
        """
        Run strategy-based resolution iterations

        Returns:
            Tuple of (resolved_versions, history)
        """
        history = []
        resolved = current_resolution.copy()

        for iteration in range(self.max_strategy_iterations):
            logger.info(f"[Strategy Iteration {iteration + 1}]")

            # Detect conflicts
            conflicts = detect_conflicts(dependency_graph)

            if not conflicts:
                logger.info("✓ No conflicts detected")
                history.append({
                    "phase": "strategy",
                    "iteration": iteration + 1,
                    "conflicts": 0,
                    "success": True
                })
                return resolved, history

            logger.info(f"Detected {len(conflicts)} conflicts")

            # Try to resolve
            resolved, success = await self.strategy.resolve(
                conflicts,
                resolved,
                dependency_graph,
                file_type
            )

            # Update graph with new versions
            for pkg, version in resolved.items():
                if pkg in dependency_graph:
                    dependency_graph[pkg]["selected_version"] = version

            history.append({
                "phase": "strategy",
                "iteration": iteration + 1,
                "conflicts": len(conflicts),
                "success": success,
                "strategy_used": self.strategy.__class__.__name__
            })

            if success:
                return resolved, history

            logger.info(f"Strategy iteration {iteration + 1} still has conflicts")

        return resolved, history


# Global engine instance (will be initialized with registries)
_engine: Optional[ResolutionEngine] = None


def get_resolution_engine(
    registry_npm=None,
    registry_pypi=None
) -> ResolutionEngine:
    """Get or create global resolution engine"""
    global _engine

    if _engine is None:
        _engine = ResolutionEngine(
            registry_npm=registry_npm,
            registry_pypi=registry_pypi
        )

    return _engine


async def resolve_conflicts(
    dependency_graph: Dict[str, Any],
    file_type: str,
    auto_resolve: bool = True,
    registry_npm=None,
    registry_pypi=None
) -> Tuple[Dict[str, str], List[Dict[str, Any]], bool]:
    """
    Convenience function to resolve conflicts

    Args:
        dependency_graph: Full dependency graph
        file_type: 'package.json' or 'requirements.txt'
        auto_resolve: If False, ask for human input
        registry_npm: NPM registry client
        registry_pypi: PyPI registry client

    Returns:
        Tuple of (resolved_versions, remaining_conflicts, success)
    """
    engine = get_resolution_engine(registry_npm, registry_pypi)
    return await engine.resolve(dependency_graph, file_type, auto_resolve)
