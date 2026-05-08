"""
Resolution strategies for handling conflicts
Implements different approaches to finding compatible versions
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ResolutionStep:
    """Records a single resolution step"""
    package: str
    from_version: Optional[str]
    to_version: str
    reason: str
    strategy: str


class ResolutionStrategy(ABC):
    """Abstract base class for resolution strategies"""

    def __init__(self, registry_npm=None, registry_pypi=None):
        """
        Initialize strategy

        Args:
            registry_npm: NPM registry client
            registry_pypi: PyPI registry client
        """
        self.registry_npm = registry_npm
        self.registry_pypi = registry_pypi
        self.steps: List[ResolutionStep] = []

    @abstractmethod
    async def resolve(
        self,
        conflicts: List[Dict[str, Any]],
        current_resolution: Dict[str, str],
        dependency_graph: Dict[str, Any],
        file_type: str
    ) -> Tuple[Dict[str, str], bool]:
        """
        Attempt to resolve conflicts using this strategy

        Args:
            conflicts: List of detected conflicts
            current_resolution: Current resolved versions
            dependency_graph: Full dependency graph
            file_type: 'package.json' or 'requirements.txt'

        Returns:
            Tuple of (resolved_versions, success)
        """
        pass

    def _get_registry(self, file_type: str):
        """Get appropriate registry for file type"""
        return self.registry_npm if file_type == "package.json" else self.registry_pypi

    def _record_step(
        self,
        package: str,
        from_version: Optional[str],
        to_version: str,
        reason: str
    ):
        """Record a resolution step"""
        self.steps.append(ResolutionStep(
            package=package,
            from_version=from_version,
            to_version=to_version,
            reason=reason,
            strategy=self.__class__.__name__
        ))


class MinimalChangeStrategy(ResolutionStrategy):
    """
    Strategy: Make minimal changes to existing versions

    Tries to resolve conflicts by making the smallest possible
    changes to the currently selected versions. This reduces risk
    of introducing new bugs from major version updates.

    Example:
    - If express 4.18.2 conflicts with something
    - Try express 4.18.1, 4.18.0 first
    - Only upgrade/downgrade if necessary
    """

    async def resolve(
        self,
        conflicts: List[Dict[str, Any]],
        current_resolution: Dict[str, str],
        dependency_graph: Dict[str, Any],
        file_type: str
    ) -> Tuple[Dict[str, str], bool]:
        """
        Resolve conflicts by making minimal version changes
        """
        if not conflicts:
            return current_resolution.copy(), True

        resolved = current_resolution.copy()
        registry = self._get_registry(file_type)
        all_resolved = True

        for conflict in conflicts:
            package = conflict["package"]
            constraint = dependency_graph.get(package, {}).get("constraint", "*")

            logger.info(f"[MinimalChange] Resolving {package}")

            # Try to find a different version with minimal change
            success = await self._find_minimal_version(
                package,
                constraint,
                current_resolution.get(package),
                registry,
                resolved
            )

            if not success:
                all_resolved = False
                logger.warning(f"[MinimalChange] Could not resolve {package}")

        return resolved, all_resolved

    async def _find_minimal_version(
        self,
        package: str,
        constraint: str,
        current_version: Optional[str],
        registry,
        resolved: Dict[str, str]
    ) -> bool:
        """
        Find a version close to the current one

        Tries versions in order of distance from current version
        """
        if not current_version:
            # No current version, try any compatible
            version = await registry.find_compatible_version(package, constraint)
            if version:
                resolved[package] = version
                self._record_step(package, None, version, "No previous version, selected compatible")
                return True
            return False

        # Get all compatible versions
        try:
            all_versions = await registry.get_versions(package)
        except Exception as e:
            logger.error(f"Failed to get versions for {package}: {e}")
            return False

        # Filter to constraint
        from core.registry.version_utils import version_satisfies_constraint
        compatible = [v for v in all_versions if version_satisfies_constraint(v, constraint)]

        if not compatible:
            return False

        # Sort by proximity to current version
        # Prefer versions close to current to minimize changes
        current_tuple = self._version_to_tuple(current_version)
        compatible_sorted = sorted(
            compatible,
            key=lambda v: abs(self._version_distance(current_tuple, self._version_to_tuple(v)))
        )

        # Try the closest compatible version
        new_version = compatible_sorted[0]
        if new_version != current_version:
            resolved[package] = new_version
            self._record_step(
                package,
                current_version,
                new_version,
                f"Minimal change from {current_version}"
            )
            return True

        return True  # Already compatible

    def _version_to_tuple(self, version: str) -> Tuple[int, ...]:
        """Convert version string to tuple of ints for comparison"""
        try:
            parts = version.split(".")
            return tuple(int(p) if p.isdigit() else 0 for p in parts)
        except (ValueError, AttributeError):
            return (0,)

    def _version_distance(self, v1: Tuple[int, ...], v2: Tuple[int, ...]) -> int:
        """Calculate distance between two versions"""
        distance = 0
        for i in range(max(len(v1), len(v2))):
            p1 = v1[i] if i < len(v1) else 0
            p2 = v2[i] if i < len(v2) else 0
            distance += abs(p1 - p2) * (10 ** (3 - i))
        return distance


class LatestVersionStrategy(ResolutionStrategy):
    """
    Strategy: Always use latest compatible versions

    Upgrades to the latest compatible version for each
    conflicting package. This ensures getting the newest
    features and bug fixes.

    Example:
    - If express conflicts
    - Upgrade to latest 4.x version
    - Or latest 5.x if constraint allows
    """

    async def resolve(
        self,
        conflicts: List[Dict[str, Any]],
        current_resolution: Dict[str, str],
        dependency_graph: Dict[str, Any],
        file_type: str
    ) -> Tuple[Dict[str, str], bool]:
        """
        Resolve conflicts by upgrading to latest compatible versions
        """
        if not conflicts:
            return current_resolution.copy(), True

        resolved = current_resolution.copy()
        registry = self._get_registry(file_type)
        all_resolved = True

        for conflict in conflicts:
            package = conflict["package"]
            constraint = dependency_graph.get(package, {}).get("constraint", "*")

            logger.info(f"[LatestVersion] Resolving {package}")

            # Find latest compatible version
            version = await registry.find_compatible_version(package, constraint)

            if version:
                old_version = resolved.get(package)
                resolved[package] = version
                self._record_step(
                    package,
                    old_version,
                    version,
                    f"Upgraded to latest compatible version"
                )
            else:
                all_resolved = False
                logger.warning(f"[LatestVersion] Could not find compatible version for {package}")

        return resolved, all_resolved


class HybridStrategy(ResolutionStrategy):
    """
    Strategy: Try minimal changes first, then latest versions

    Combines both strategies:
    1. First, try minimal changes (safest)
    2. If that fails, try latest versions (more aggressive)

    This balances safety with effectiveness.
    """

    def __init__(self, registry_npm=None, registry_pypi=None):
        """Initialize hybrid strategy with both sub-strategies"""
        super().__init__(registry_npm, registry_pypi)
        self.minimal_strategy = MinimalChangeStrategy(registry_npm, registry_pypi)
        self.latest_strategy = LatestVersionStrategy(registry_npm, registry_pypi)

    async def resolve(
        self,
        conflicts: List[Dict[str, Any]],
        current_resolution: Dict[str, str],
        dependency_graph: Dict[str, Any],
        file_type: str
    ) -> Tuple[Dict[str, str], bool]:
        """
        Try minimal first, then fallback to latest
        """
        logger.info("[Hybrid] Trying minimal change strategy first")
        resolved, success = await self.minimal_strategy.resolve(
            conflicts,
            current_resolution,
            dependency_graph,
            file_type
        )

        if success:
            logger.info("[Hybrid] Minimal strategy succeeded")
            self.steps = self.minimal_strategy.steps
            return resolved, True

        logger.info("[Hybrid] Minimal strategy failed, trying latest versions")
        resolved, success = await self.latest_strategy.resolve(
            conflicts,
            current_resolution,
            dependency_graph,
            file_type
        )

        if success:
            logger.info("[Hybrid] Latest strategy succeeded")
            self.steps = self.latest_strategy.steps
            return resolved, True

        logger.warning("[Hybrid] Both strategies failed")
        self.steps = self.minimal_strategy.steps + self.latest_strategy.steps
        return resolved, False
