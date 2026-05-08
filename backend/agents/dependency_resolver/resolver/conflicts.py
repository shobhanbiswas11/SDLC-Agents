"""
Conflict detection — finds packages required with incompatible constraints.
"""
from __future__ import annotations
import logging
from typing import Dict, List, Any
from agents.dependency_resolver.registry.version_utils import version_satisfies_constraint
from agents.dependency_resolver.schemas import Conflict

logger = logging.getLogger(__name__)


class ConflictSet:
    def __init__(self, graph_dict: Dict[str, Any]):
        self.graph = graph_dict
        self.conflicts: List[Conflict] = []

    def detect(self) -> List[Conflict]:
        """Detect version conflicts across the full dependency graph."""
        self.conflicts = []
        # Build map: package → { requester: constraint }
        requirements: Dict[str, Dict[str, str]] = {}

        for pkg_name, info in self.graph.items():
            version   = info.get("version")
            constraint = info.get("constraint", "*")
            parents   = info.get("parents", [])

            # Record this package's own constraint from its parent chain
            if not parents:
                requirements.setdefault(pkg_name, {})["<root>"] = constraint
            for parent in parents:
                parent_version = self.graph.get(parent, {}).get("version", "*")
                requirements.setdefault(pkg_name, {})[parent] = constraint

        # Check every package: are all requesters' constraints satisfiable?
        for pkg_name, requesters in requirements.items():
            version = self.graph.get(pkg_name, {}).get("version")
            if not version:
                continue
            failing = {
                req: con
                for req, con in requesters.items()
                if con != "*" and not version_satisfies_constraint(version, con)
            }
            if failing:
                self.conflicts.append(Conflict(
                    package=pkg_name,
                    requested_by=requesters,
                    resolution=version,
                    explanation=None,
                ))

        logger.info(f"ConflictDetector: {len(self.conflicts)} conflicts found")
        return self.conflicts
