"""
Constraint solver — intersect version constraints per package and identify conflicts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import networkx as nx

from app.utils.version_utils import intersect_specifiers

logger = logging.getLogger(__name__)


@dataclass
class ConstraintResult:
    """The result of constraint solving for a single package."""

    package: str
    constraints: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)  # which packages impose this constraint
    status: str = "ok"  # "ok" | "conflict" | "unconstrained"


def collect_constraints(G: nx.DiGraph) -> dict[str, ConstraintResult]:
    """
    Walk the graph and collect version constraints per package.

    For each node that is a dependency target, gather the specifier
    from the parent edge and the node attributes.
    """
    constraints: dict[str, ConstraintResult] = {}

    for node_name, attrs in G.nodes(data=True):
        spec = attrs.get("specifier", "")
        if node_name not in constraints:
            constraints[node_name] = ConstraintResult(package=node_name)

        # Include root specifier if this is a top-level node with no parents
        if spec and not list(G.predecessors(node_name)):
            constraints[node_name].constraints.append(spec)
            if "root" not in constraints[node_name].sources:
                constraints[node_name].sources.append("root")

    for parent, child, attrs in G.edges(data=True):
        spec = attrs.get("specifier", "")
        if child not in constraints:
            constraints[child] = ConstraintResult(package=child)
        if spec:
            constraints[child].constraints.append(spec)
        if parent not in constraints[child].sources:
            constraints[child].sources.append(parent)

    return constraints


def solve_constraints(G: nx.DiGraph) -> list[ConstraintResult]:
    """
    For every package in the graph with ≥ 2 constraints, try to intersect
    them.  Return a list of ConstraintResults with status set accordingly.
    """
    all_constraints = collect_constraints(G)
    results: list[ConstraintResult] = []

    for pkg, cr in all_constraints.items():
        if not cr.constraints:
            cr.status = "unconstrained"
        elif len(cr.constraints) == 1:
            cr.status = "ok"
        else:
            merged = intersect_specifiers(cr.constraints)
            if merged is None:
                cr.status = "conflict"
            else:
                # Even if parseable, the intersection might be empty
                # We can't fully verify without available versions, so mark ok
                cr.status = "ok"
        results.append(cr)

    return results
