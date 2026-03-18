"""
FastAPI application — the main entry-point for the Dependency Resolver Agent API.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.analysis.conflict_detector import detect_conflicts
from app.analysis.conflict_explainer import explain_conflicts
from app.analysis.upgrade_suggester import suggest_upgrades
from app.config import get_settings
from app.parser.node_parser import parse_node_deps
from app.parser.python_parser import parse_python_deps
from app.reports.report_generator import (
    DependencyReport,
    generate_report,
    report_to_dict,
)
from app.resolver.dependency_resolver import resolve_node, resolve_python
from app.resolver.graph_builder import build_graph
from app.services.repo_service import Ecosystem, cleanup_repo, load_repo
from app.utils.http import close_http_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Dependency Resolver Agent starting up")
    yield
    await close_http_client()
    logger.info("🛑 Dependency Resolver Agent shutting down")


# ── App ───────────────────────────────────────────────────────

app = FastAPI(
    title="Dependency Resolver Agent",
    description="Analyses repositories, resolves dependencies recursively, detects conflicts, and generates AI-explained reports.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────


class ResolveRequest(BaseModel):
    repo_url: str


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "dependency-resolver-agent"


# ── Routes ────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@app.post("/resolve")
async def resolve(req: ResolveRequest) -> dict[str, Any]:
    """
    Resolve all dependencies for a repository.

    Body: `{ "repo_url": "<url or local path>" }`
    """
    try:
        # 1. Clone / load repo
        logger.info("Loading repo: %s", req.repo_url)
        repo_info = load_repo(req.repo_url)
        logger.info(
            "Detected ecosystems: %s",
            [e.value for e in repo_info.ecosystems],
        )

        all_reports: list[dict[str, Any]] = []

        # 2. Resolve per ecosystem
        for eco in repo_info.ecosystems:
            dep_files = repo_info.dependency_files.get(eco, [])

            if eco == Ecosystem.PYTHON:
                deps = parse_python_deps(dep_files)
                logger.info("Parsed %d Python dependencies", len(deps))
                result = await resolve_python(deps)
            elif eco == Ecosystem.NODE:
                deps = parse_node_deps(dep_files)
                logger.info("Parsed %d Node dependencies", len(deps))
                result = await resolve_node(deps)
            else:
                continue

            # 3. Build graph
            G = build_graph(result)
            logger.info("Graph: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())

            # 4. Detect conflicts
            conflict_report = detect_conflicts(G)
            logger.info("Conflicts detected: %d", conflict_report.conflict_count)

            # 5. AI explanations (best-effort)
            explanations = explain_conflicts(conflict_report)

            # 6. AI upgrade suggestions (best-effort)
            suggestions = suggest_upgrades(result, conflict_report)

            # 7. Generate report
            report = generate_report(
                result, G, conflict_report, explanations, suggestions
            )
            all_reports.append(report_to_dict(report))

        # Cleanup cloned repo
        cleanup_repo(repo_info)

        # Return combined results
        if len(all_reports) == 1:
            return all_reports[0]

        return {
            "ecosystems": [r["ecosystem"] for r in all_reports],
            "reports": all_reports,
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Resolution failed")
        raise HTTPException(status_code=500, detail=str(e))
