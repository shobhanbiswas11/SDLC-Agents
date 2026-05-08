"""
Backtracking solver for complex dependency resolution
Uses systematic search to find valid solutions
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from core.conflict_detector import detect_conflicts
from core.registry.version_utils import version_satisfies_constraint

logger = logging.getLogger(__name__)


class BacktrackingSolver:
    """
    Solves dependency conflicts using backtracking algorithm

    Systematically explores the solution space, pruning branches
    that lead to conflicts. Used when greedy strategies fail.
    """

    def __init__(self, registry_npm=None, registry_pypi=None, max_iterations: int = 100):
        """
        Initialize backtracking solver

        Args:
            registry_npm: NPM registry client
            registry_pypi: PyPI registry client
            max_iterations: Maximum backtracking iterations
        """
        self.registry_npm = registry_npm
        self.registry_pypi = registry_pypi
        self.max_iterations = max_iterations
        self.iteration_count = 0
        self.solutions_found = 0

    async def solve(
        self,
        dependency_graph: Dict[str, Any],
        current_resolution: Dict[str, str],
        file_type: str
    ) -> Tuple[Optional[Dict[str, str]], int]:
        """
        Solve using backtracking

        Args:
            dependency_graph: Full dependency graph
            current_resolution: Current (possibly conflicted) resolution
            file_type: 'package.json' or 'requirements.txt'

        Returns:
            Tuple of (solution, iterations_used) or (None, iterations_used)
        """
        self.iteration_count = 0
        self.solutions_found = 0
        registry = self.registry_npm if file_type == "package.json" else self.registry_pypi

        # Get packages that need resolution
        packages_to_resolve = list(dependency_graph.keys())

        logger.info(f"[Backtracker] Starting search with {len(packages_to_resolve)} packages")

        # Try backtracking
        solution = await self._backtrack(
            packages_to_resolve,
            0,
            current_resolution.copy(),
            dependency_graph,
            registry,
            set()
        )

        logger.info(f"[Backtracker] Completed after {self.iteration_count} iterations")
        logger.info(f"[Backtracker] Found {self.solutions_found} valid solutions")

        return solution, self.iteration_count

    async def _backtrack(
        self,
        packages: List[str],
        index: int,
        current_resolution: Dict[str, str],
        dependency_graph: Dict[str, Any],
        registry,
        tried_versions: Set[Tuple[str, str]]
    ) -> Optional[Dict[str, str]]:
        """
        Recursive backtracking function

        Args:
            packages: List of packages to resolve
            index: Current index in packages list
            current_resolution: Current version assignments
            dependency_graph: Full dependency graph
            registry: Registry client
            tried_versions: Set of (package, version) pairs already tried

        Returns:
            Valid solution or None if not found
        """
        self.iteration_count += 1

        if self.iteration_count > self.max_iterations:
            logger.warning("[Backtracker] Max iterations reached")
            return None

        # Base case: all packages assigned
        if index == len(packages):
            # Check if current resolution is valid
            conflicts = detect_conflicts(dependency_graph)
            if not conflicts:
                logger.info("[Backtracker] Found valid solution!")
                self.solutions_found += 1
                return current_resolution.copy()
            return None

        package = packages[index]
        constraint = dependency_graph[package].get("constraint", "*")

        logger.debug(f"[Backtracker] Processing {package} with constraint {constraint}")

        # Get available versions for this package
        try:
            versions = await registry.get_versions(package)
        except Exception as e:
            logger.warning(f"[Backtracker] Failed to get versions for {package}: {e}")
            return None

        # Filter to constraint
        compatible = [v for v in versions if version_satisfies_constraint(v, constraint)]

        if not compatible:
            logger.debug(f"[Backtracker] No compatible versions for {package}")
            return None

        # Try versions in reverse order (latest first)
        for version in reversed(compatible):
            version_key = (package, version)

            if version_key in tried_versions:
                continue

            tried_versions.add(version_key)

            # Assign this version
            current_resolution[package] = version

            # Recursively try to resolve remaining packages
            solution = await self._backtrack(
                packages,
                index + 1,
                current_resolution,
                dependency_graph,
                registry,
                tried_versions
            )

            if solution is not None:
                return solution

            # Backtrack: undo assignment
            del current_resolution[package]

        logger.debug(f"[Backtracker] No solution found for {package}")
        return None


async def backtrack_solve(
    dependency_graph: Dict[str, Any],
    current_resolution: Dict[str, str],
    file_type: str,
    registry_npm=None,
    registry_pypi=None,
    max_iterations: int = 100
) -> Tuple[Optional[Dict[str, str]], int]:
    """
    Convenience function for backtracking

    Args:
        dependency_graph: Full dependency graph
        current_resolution: Current resolution
        file_type: 'package.json' or 'requirements.txt'
        registry_npm: NPM registry client
        registry_pypi: PyPI registry client
        max_iterations: Maximum iterations

    Returns:
        Tuple of (solution, iterations) or (None, iterations)
    """
    solver = BacktrackingSolver(
        registry_npm=registry_npm,
        registry_pypi=registry_pypi,
        max_iterations=max_iterations
    )
    return await solver.solve(dependency_graph, current_resolution, file_type)
