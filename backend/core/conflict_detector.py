"""
Conflict detection engine
Identifies version conflicts and incompatibilities in dependency graphs
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Conflict:
    """Represents a detected conflict"""
    package: str
    constraints: List[str]
    reason: str
    severity: str = "error"  # error, warning, info

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "package": self.package,
            "constraints": self.constraints,
            "reason": self.reason,
            "severity": self.severity
        }


class ConflictDetector:
    """Detects version conflicts in dependency graphs"""

    def __init__(self):
        pass

    def detect_conflicts(
        self,
        dependency_graph: Dict[str, Dict[str, Any]]
    ) -> List[Conflict]:
        """
        Detect all conflicts in a dependency graph

        Args:
            dependency_graph: Dict mapping package -> {constraint, dependencies, ...}

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Check for direct conflicts (same package required with incompatible versions)
        conflicts.extend(self._detect_version_conflicts(dependency_graph))

        # Check for missing transitive dependencies
        conflicts.extend(self._detect_missing_dependencies(dependency_graph))

        # Check for circular dependencies
        conflicts.extend(self._detect_circular_dependencies(dependency_graph))

        # Check for peer dependency issues
        conflicts.extend(self._detect_peer_dependency_issues(dependency_graph))

        return conflicts

    def _detect_version_conflicts(
        self,
        dependency_graph: Dict[str, Dict[str, Any]]
    ) -> List[Conflict]:
        """
        Detect when the same package is required with incompatible version constraints

        Example:
        - packageA requires: "lodash": "^4.0.0"
        - packageB requires: "lodash": "^3.0.0"
        These are incompatible.
        """
        conflicts = []

        # Build a map of all constraints for each package
        package_constraints: Dict[str, List[Tuple[str, str]]] = {}

        def collect_constraints(pkg: str, constraints_dict: Dict[str, str]):
            """Recursively collect all constraints"""
            for dep_name, constraint in constraints_dict.items():
                if dep_name not in package_constraints:
                    package_constraints[dep_name] = []
                package_constraints[dep_name].append((pkg, constraint))

        # Collect constraints from all nodes
        for package, info in dependency_graph.items():
            if "dependencies" in info:
                collect_constraints(package, info["dependencies"])

        # Check for conflicts
        for package, constraints in package_constraints.items():
            if len(constraints) > 1:
                # Multiple packages depend on this package
                constraint_strs = [c[1] for c in constraints]
                requester_info = [f"{c[0]} (requires {c[1]})" for c in constraints]

                # Check if constraints are compatible
                if not self._constraints_compatible(constraint_strs):
                    reason = f"Incompatible constraints from: {'; '.join(requester_info)}"
                    conflicts.append(Conflict(
                        package=package,
                        constraints=constraint_strs,
                        reason=reason,
                        severity="error"
                    ))

        return conflicts

    def _detect_missing_dependencies(
        self,
        dependency_graph: Dict[str, Dict[str, Any]]
    ) -> List[Conflict]:
        """
        Detect when a dependency is required but not in the graph
        """
        conflicts = []
        all_packages = set(dependency_graph.keys())

        for package, info in dependency_graph.items():
            if "dependencies" not in info:
                continue

            for dep_name, constraint in info["dependencies"].items():
                if dep_name not in all_packages:
                    reason = f"Required by {package} but not available in registry"
                    conflicts.append(Conflict(
                        package=dep_name,
                        constraints=[constraint],
                        reason=reason,
                        severity="error"
                    ))

        return conflicts

    def _detect_circular_dependencies(
        self,
        dependency_graph: Dict[str, Dict[str, Any]]
    ) -> List[Conflict]:
        """
        Detect circular dependencies (A -> B -> A)
        """
        conflicts = []

        def has_cycle(start: str, current: str, visited: Set[str], path: List[str]):
            """Check if there's a cycle using DFS"""
            if current in visited:
                if current == start:
                    return path + [current]
                return None

            visited.add(current)
            path.append(current)

            if current in dependency_graph:
                deps = dependency_graph[current].get("dependencies", {})
                for dep in deps.keys():
                    cycle = has_cycle(start, dep, visited.copy(), path.copy())
                    if cycle:
                        return cycle

            return None

        # Check each package
        for package in dependency_graph.keys():
            cycle = has_cycle(package, package, set(), [])
            if cycle:
                cycle_str = " -> ".join(cycle)
                conflicts.append(Conflict(
                    package=package,
                    constraints=[],
                    reason=f"Circular dependency detected: {cycle_str}",
                    severity="error"
                ))

        return conflicts

    def _detect_peer_dependency_issues(
        self,
        dependency_graph: Dict[str, Dict[str, Any]]
    ) -> List[Conflict]:
        """
        Detect issues with peer dependencies
        (packages that should be installed at the same level)

        Note: This is a placeholder for future implementation
        Peer dependencies are less common in Python than JavaScript
        """
        conflicts = []

        # TODO: Implement peer dependency detection
        # This requires package metadata about peer dependencies
        # from the registry

        return conflicts

    def _constraints_compatible(self, constraints: List[str]) -> bool:
        """
        Check if a set of version constraints are compatible

        Args:
            constraints: List of constraint strings

        Returns:
            True if all constraints can be satisfied by at least one version
        """
        if len(constraints) <= 1:
            return True

        # Simple heuristic: check if ranges overlap
        # More sophisticated: would need to fetch actual available versions
        # and test combinations

        # For now, use a basic approach:
        # If constraints have significantly different major versions, they conflict
        for i, c1 in enumerate(constraints):
            for c2 in constraints[i+1:]:
                if not self._ranges_overlap(c1, c2):
                    return False

        return True

    def _ranges_overlap(self, constraint1: str, constraint2: str) -> bool:
        """
        Simple check if two version constraint ranges might overlap

        Returns True if they could overlap (conservative estimate)
        """
        # Extract major versions from constraints
        # This is very simplified - real implementation would use
        # version range intersection logic

        majors1 = self._extract_major_versions(constraint1)
        majors2 = self._extract_major_versions(constraint2)

        # If both have major versions, check for overlap
        if majors1 and majors2:
            # Check if any major version appears in both
            return any(m in majors2 for m in majors1)

        # Conservative: assume they might overlap
        return True

    def _extract_major_versions(self, constraint: str) -> Set[int]:
        """Extract possible major versions from a constraint"""
        majors = set()

        # Simple parsing of common constraint formats
        import re

        # Handle "^X.Y.Z" (allows X.* where X > 0)
        if constraint.startswith("^"):
            match = re.match(r"\^(\d+)\.", constraint)
            if match:
                major = int(match.group(1))
                majors.add(major)

        # Handle "~X.Y.Z" (allows X.Y.*)
        elif constraint.startswith("~"):
            match = re.match(r"~(\d+)\.", constraint)
            if match:
                major = int(match.group(1))
                majors.add(major)

        # Handle ">=X.Y.Z" - could be any version >= X
        elif constraint.startswith(">="):
            match = re.match(r">=(\d+)\.", constraint)
            if match:
                major = int(match.group(1))
                for i in range(major, major + 5):
                    majors.add(i)

        # Handle "X.Y.Z" exact
        else:
            match = re.match(r"(\d+)\.", constraint)
            if match:
                major = int(match.group(1))
                majors.add(major)

        return majors


# Global detector instance
detector = ConflictDetector()


def detect_conflicts(
    dependency_graph: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Detect conflicts in a dependency graph

    Returns list of conflict dicts for JSON serialization
    """
    conflicts = detector.detect_conflicts(dependency_graph)
    return [c.to_dict() for c in conflicts]
