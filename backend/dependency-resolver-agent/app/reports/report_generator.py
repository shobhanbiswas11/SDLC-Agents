"""
Report generator — assembles the final resolution report.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.analysis.conflict_detector import ConflictReport
from app.resolver.dependency_resolver import ResolutionResult
from app.resolver.graph_builder import graph_to_dict

import networkx as nx


@dataclass
class DependencyReport:
    """The full report returned by the API."""

    ecosystem: str = ""
    root_dependencies: list[str] = field(default_factory=list)
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    graph: dict[str, Any] = field(default_factory=dict)
    ai_explanations: list[dict[str, str]] = field(default_factory=list)
    ai_suggestions: list[dict[str, str]] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)
    total_packages: int = 0
    conflict_count: int = 0


def generate_report(
    result: ResolutionResult,
    G: nx.DiGraph,
    conflict_report: ConflictReport,
    explanations: list[dict[str, str]] | None = None,
    suggestions: list[dict[str, str]] | None = None,
) -> DependencyReport:
    """
    Build the final DependencyReport from all resolution artefacts.
    """
    deps = []
    for name, node in result.resolved.items():
        deps.append({
            "name": node.name,
            "version": node.version or "",
            "specifier": node.specifier,
            "ecosystem": node.ecosystem,
            "children": node.children,
        })

    conflicts = []
    for c in conflict_report.conflicts:
        conflicts.append({
            "package": c.package,
            "constraints": c.constraints,
            "sources": c.sources,
            "status": c.status,
            "description": c.description,
        })

    return DependencyReport(
        ecosystem=result.ecosystem,
        root_dependencies=result.root_dependencies,
        dependencies=deps,
        conflicts=conflicts,
        graph=graph_to_dict(G),
        ai_explanations=explanations or [],
        ai_suggestions=suggestions or [],
        cycles=conflict_report.cycles,
        total_packages=conflict_report.total_packages,
        conflict_count=conflict_report.conflict_count,
    )


def report_to_dict(report: DependencyReport) -> dict[str, Any]:
    """Serialise the report to a JSON-friendly dict."""
    return asdict(report)


def format_report_text(report: DependencyReport) -> str:
    """
    Produce a human-readable plain-text report.
    """
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("  Dependency Resolution Report")
    lines.append("=" * 60)
    lines.append(f"\nEcosystem: {report.ecosystem}")
    lines.append(f"Total packages resolved: {report.total_packages}")
    lines.append(f"Conflicts found: {report.conflict_count}")

    lines.append(f"\n── Root Dependencies ({len(report.root_dependencies)}) ──")
    for r in report.root_dependencies:
        lines.append(f"  • {r}")

    lines.append(f"\n── Resolved Dependencies ({len(report.dependencies)}) ──")
    for d in report.dependencies:
        ver = d.get("version", "")
        spec = d.get("specifier", "")
        label = f"{d['name']} {ver}" + (f" ({spec})" if spec else "")
        lines.append(f"  • {label}")

    if report.conflicts:
        lines.append(f"\n── Conflicts ({report.conflict_count}) ──")
        for c in report.conflicts:
            lines.append(f"  ✗ {c['package']}: {', '.join(c.get('constraints', []))}")
            if c.get("description"):
                lines.append(f"    {c['description']}")

    if report.cycles:
        lines.append(f"\n── Circular Dependencies ({len(report.cycles)}) ──")
        for cyc in report.cycles:
            lines.append(f"  ↻ {' → '.join(cyc)}")

    if report.ai_explanations:
        lines.append("\n── AI Explanations ──")
        for ex in report.ai_explanations:
            lines.append(f"  [{ex['package']}] {ex['explanation']}")

    if report.ai_suggestions:
        lines.append("\n── AI Upgrade Suggestions ──")
        for s in report.ai_suggestions:
            lines.append(f"  [{s['package']}] {s['suggestion']}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)
