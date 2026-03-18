"""
Conflict detector — find version conflicts in the dependency graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from app.resolver.constraint_solver import ConstraintResult, solve_constraints
from app.resolver.graph_builder import detect_cycles


@dataclass
class Conflict:
    """Represents a detected dependency conflict."""

    package: str
    constraints: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    status: str = "conflict"
    description: str = ""


@dataclass
class ConflictReport:
    """Summary of all detected conflicts."""

    conflicts: list[Conflict] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)
    total_packages: int = 0
    conflict_count: int = 0


def detect_conflicts(G: nx.DiGraph) -> ConflictReport:
    """
    Analyse a dependency graph for version conflicts and circular dependencies.
    """
    constraint_results: list[ConstraintResult] = solve_constraints(G)
    cycles = detect_cycles(G)

    conflicts: list[Conflict] = []
    for cr in constraint_results:
        if cr.status == "conflict":
            conflicts.append(
                Conflict(
                    package=cr.package,
                    constraints=cr.constraints,
                    sources=cr.sources,
                    description=(
                        f"Package '{cr.package}' has conflicting version constraints: "
                        f"{', '.join(cr.constraints)} "
                        f"(required by: {', '.join(cr.sources) if cr.sources else 'root'})"
                    ),
                )
            )

    return ConflictReport(
        conflicts=conflicts,
        cycles=cycles,
        total_packages=G.number_of_nodes(),
        conflict_count=len(conflicts),
    )
