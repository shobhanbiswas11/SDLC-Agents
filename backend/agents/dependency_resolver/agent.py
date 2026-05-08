"""
Headless (non-interactive) resolver pipeline.
Used by the REST /resolve, /diff, /audit endpoints and by CI.
The HITL path runs in orchestrator.py instead.
"""
from __future__ import annotations
import logging
import uuid
from typing import List

from agents.dependency_resolver.schemas import (
    ResolveRequest, ResolveResponse, AuditResponse, DiffRequest, DiffResponse,
    ResolvedPackage, Conflict,
)
from agents.dependency_resolver.parsers import get_parser
from agents.dependency_resolver.resolver.graph import DependencyGraph
from agents.dependency_resolver.resolver.solver import PubGrubSolver
from agents.dependency_resolver.security.osv_client import OSVClient
from agents.dependency_resolver.security.license_check import LicenseChecker
from agents.dependency_resolver.llm.explainer import DependencyExplainer

logger = logging.getLogger(__name__)
_explainer = DependencyExplainer()


async def execute_resolve(payload: ResolveRequest) -> ResolveResponse:
    trace_id = str(uuid.uuid4())
    logger.info(f"[{trace_id}] resolve start: {payload.ecosystem} strategy={payload.strategy}")

    # 1. Parse
    parser = get_parser(payload.ecosystem)
    direct = parser.parse(payload.manifest)

    # 2. Build graph
    graph = DependencyGraph(payload.ecosystem)
    await graph.build(direct, include_dev=payload.include_dev)
    graph_dict = graph.to_dict()

    # 3. Solve
    solver = PubGrubSolver(payload.ecosystem, strategy=payload.strategy)
    resolved, conflicts = await solver.solve(graph_dict)

    # 4. Audit CVEs
    if payload.check_vulnerabilities:
        osv = OSVClient()
        pkg_dicts = [p.model_dump() for p in resolved]
        annotated = await osv.annotate_packages(pkg_dicts, payload.ecosystem)
        vuln_map = {p["name"]: p.get("vulnerabilities", []) for p in annotated}
        for pkg in resolved:
            pkg.vulnerabilities = vuln_map.get(pkg.name, [])

    # 5. Explain (if requested)
    explanation = ""
    if payload.explain and conflicts:
        explanation = await _explainer.explain_conflicts(conflicts, resolved)

    # 6. Build outputs
    lockfile = _explainer.build_lockfile(resolved, payload.ecosystem)
    license_issues = LicenseChecker().check([p.model_dump() for p in resolved])
    report = _explainer.build_report(
        resolved, conflicts, payload.ecosystem, payload.strategy,
        explanation, license_issues, lockfile,
    )

    logger.info(
        f"[{trace_id}] done: {len(resolved)} resolved, "
        f"{len(conflicts)} conflicts, "
        f"{sum(len(p.vulnerabilities) for p in resolved)} CVEs"
    )
    return ResolveResponse(
        ok=len(conflicts) == 0,
        resolved=resolved,
        conflicts=conflicts,
        lockfile=lockfile,
        report_markdown=report,
        trace_id=trace_id,
    )


async def execute_diff(payload: DiffRequest) -> DiffResponse:
    trace_id = str(uuid.uuid4())
    old_resp = await execute_resolve(payload.old)
    new_resp = await execute_resolve(payload.new)

    old_map = {p.name: p for p in old_resp.resolved}
    new_map = {p.name: p for p in new_resp.resolved}

    added:      List[ResolvedPackage] = []
    removed:    List[ResolvedPackage] = []
    upgraded:   List[dict] = []
    downgraded: List[dict] = []
    unchanged = 0

    for name, pkg in new_map.items():
        if name not in old_map:
            added.append(pkg)
        else:
            old_pkg = old_map[name]
            if old_pkg.version == pkg.version:
                unchanged += 1
            else:
                try:
                    from packaging.version import Version
                    if Version(pkg.version) > Version(old_pkg.version):
                        upgraded.append({"name": name, "from": old_pkg.version, "to": pkg.version})
                    else:
                        downgraded.append({"name": name, "from": old_pkg.version, "to": pkg.version})
                except Exception:
                    upgraded.append({"name": name, "from": old_pkg.version, "to": pkg.version})

    for name, pkg in old_map.items():
        if name not in new_map:
            removed.append(pkg)

    return DiffResponse(
        added=added, removed=removed,
        upgraded=upgraded, downgraded=downgraded,
        unchanged=unchanged, trace_id=trace_id,
    )


async def execute_audit(payload: ResolveRequest) -> AuditResponse:
    trace_id = str(uuid.uuid4())
    parser = get_parser(payload.ecosystem)
    direct = parser.parse(payload.manifest)
    graph  = DependencyGraph(payload.ecosystem)
    await graph.build(direct)
    graph_dict = graph.to_dict()

    solver = PubGrubSolver(payload.ecosystem, strategy=payload.strategy)
    resolved, _ = await solver.solve(graph_dict)

    osv = OSVClient()
    pkg_dicts = [p.model_dump() for p in resolved]
    annotated = await osv.annotate_packages(pkg_dicts, payload.ecosystem)
    vuln_map = {p["name"]: p.get("vulnerabilities", []) for p in annotated}
    for pkg in resolved:
        pkg.vulnerabilities = vuln_map.get(pkg.name, [])

    vulnerable = [p for p in resolved if p.vulnerabilities]
    license_issues = LicenseChecker().check([p.model_dump() for p in resolved])

    cve_count = sum(len(p.vulnerabilities) for p in resolved)
    lines = [f"# Security Audit Report\n",
             f"**Packages scanned**: {len(resolved)}  ",
             f"**Vulnerable**: {len(vulnerable)}  ",
             f"**Total CVEs**: {cve_count}  ",
             f"**License issues**: {len(license_issues)}\n"]
    for p in vulnerable:
        lines.append(f"- **{p.name}@{p.version}**: {', '.join(p.vulnerabilities)}")

    return AuditResponse(
        total_packages=len(resolved),
        vulnerable=vulnerable,
        license_issues=license_issues,
        report_markdown="\n".join(lines),
        trace_id=trace_id,
    )
