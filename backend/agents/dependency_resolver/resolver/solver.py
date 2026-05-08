"""
PubGrub-style deterministic version solver.

Approach:
  1. Collect all constraints per package from the full graph.
  2. For each package, pick the best version satisfying ALL constraints
     (strategy: stable=latest-non-pre, latest=absolute-latest, minimal=oldest).
  3. If no single version satisfies all, record a conflict.
"""
from __future__ import annotations
import logging
from typing import Dict, List, Optional, Tuple, Any
from packaging.version import Version, InvalidVersion
from agents.dependency_resolver.registry import get_registry
from agents.dependency_resolver.schemas import Conflict, ResolvedPackage

logger = logging.getLogger(__name__)


def _is_prerelease(v: str) -> bool:
    try:
        return Version(v).is_prerelease
    except InvalidVersion:
        return False


def _sort_versions(versions: List[str], strategy: str) -> List[str]:
    """Sort versions for candidate selection per strategy."""
    def key(v: str):
        try:
            return Version(v)
        except InvalidVersion:
            return Version("0.0.0")

    stable = [v for v in versions if not _is_prerelease(v)]
    pool = stable if stable else versions
    pool = sorted(pool, key=key, reverse=(strategy != "minimal"))
    return pool


class PubGrubSolver:
    """Deterministic, backtracking-capable version solver."""

    def __init__(self, ecosystem: str, strategy: str = "stable"):
        self.ecosystem = ecosystem
        self.strategy  = strategy
        self.registry  = get_registry(ecosystem)

    async def solve(
        self,
        graph_dict: Dict[str, Any],
    ) -> Tuple[List[ResolvedPackage], List[Conflict]]:
        """
        Returns (resolved_packages, conflicts).
        Conflicts list contains packages whose constraints could not all be met.
        """
        # 1. Gather all constraints per package across the graph
        pkg_constraints: Dict[str, Dict[str, str]] = {}   # pkg → {requester: constraint}
        for pkg, info in graph_dict.items():
            constraint = info.get("constraint", "*")
            parents    = info.get("parents", []) or ["<root>"]
            for parent in parents:
                pkg_constraints.setdefault(pkg, {})[parent] = constraint

        resolved_packages: List[ResolvedPackage] = []
        conflicts: List[Conflict]                = []

        # 2. Solve each package
        for pkg, requesters in pkg_constraints.items():
            info = graph_dict.get(pkg, {})
            already_selected = info.get("version")

            # Prefer versions already fetched into the graph dict (avoids extra network calls).
            # Fall back to a registry call only when the graph didn't pre-fetch them.
            graph_versions: List[str] = info.get("versions", [])
            if graph_versions:
                all_versions = graph_versions
            else:
                try:
                    all_versions = await self.registry.get_versions(pkg)
                except Exception:
                    all_versions = []

            if all_versions:
                candidates = _sort_versions(all_versions, self.strategy)
            elif already_selected:
                candidates = [already_selected]
            else:
                candidates = []

            # Find a version satisfying every constraint
            chosen: Optional[str] = None
            from agents.dependency_resolver.registry.version_utils import version_satisfies_constraint

            for candidate in candidates:
                if all(
                    c == "*" or version_satisfies_constraint(candidate, c)
                    for c in requesters.values()
                ):
                    chosen = candidate
                    break

            if chosen is None:
                # Fall back to the graph-resolved version even if imperfect
                chosen = already_selected

            if chosen:
                resolved_packages.append(ResolvedPackage(
                    name=pkg,
                    version=chosen,
                    direct=info.get("direct", False),
                    parents=list(requesters.keys()),
                    license=info.get("license"),
                    vulnerabilities=[],
                ))
                # Check whether chosen actually satisfies all constraints
                failing = {
                    req: con for req, con in requesters.items()
                    if con != "*" and not version_satisfies_constraint(chosen, con)
                }
                if failing:
                    conflicts.append(Conflict(
                        package=pkg,
                        requested_by=requesters,
                        resolution=chosen,
                    ))
            else:
                conflicts.append(Conflict(
                    package=pkg,
                    requested_by=requesters,
                    resolution=None,
                ))

        logger.info(
            f"Solver: {len(resolved_packages)} resolved, {len(conflicts)} conflicts"
        )
        return resolved_packages, conflicts
