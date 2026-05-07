"""
Coding Standards Enforcer agent — FastAPI router.

REST endpoints
    GET  /                       health
    GET  /languages              supported languages metadata
    POST /repo-files             clone repo + return source tree
    POST /repo-branches          list remote branches
    POST /analyze                LLM analysis of a code blob
    POST /fix                    LLM fix-all + diff
    POST /scan                   streaming repo scan (NDJSON)
    POST /apply-linters          black/isort/autopep8/autoflake + re-scan
    GET  /download-fixed         zip the corrected repo
    GET  /corrected-files        return all source files as JSON
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import traceback
from pathlib import Path

import json

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse

from agents.coding_standards_enforcer.hitl.orchestrator import HITLOrchestrator

from agents.coding_standards_enforcer.agent import (
    analyze_code,
    apply_linters_to_repo,
    fix_all_violations,
    generate_diff,
    load_repo_files_for_editor,
    polish_code,
    stream_scan,
)
from agents.coding_standards_enforcer.parsers import (
    get_all_supported_extensions,
)
from agents.coding_standards_enforcer.parsers.language_detector import SKIP_DIRS
from agents.coding_standards_enforcer.prompts import (
    LANGUAGE_STANDARDS,
    get_supported_languages,
)
from agents.coding_standards_enforcer.repo.git_client import (
    clone_repository,
    list_remote_branches,
)
from agents.coding_standards_enforcer.schemas import (
    AnalyzeRequest,
    ApplyLintersRequest,
    ApprovalResponse,
    CloneRepoRequest,
    CreateSessionRequest,
    CreateSessionResponse,
    FixAllRequest,
    PolishRequest,
    RepoBranchesRequest,
    ScanRequest,
)

logger = logging.getLogger(__name__)

agent_router = APIRouter(
    prefix="/coding_standards_enforcer",
    tags=["Coding Standards Enforcer"],
)

# Single orchestrator instance shared across all HITL endpoints.
_orchestrator = HITLOrchestrator()


# ─────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────


@agent_router.get("/health")
def health():
    return {"status": "Coding Standards Enforcer running — Multi-Language Agent Mode"}


# ─────────────────────────────────────────────────────────────
# Languages
# ─────────────────────────────────────────────────────────────


@agent_router.get("/languages")
def supported_languages():
    languages = []
    for key, info in LANGUAGE_STANDARDS.items():
        languages.append(
            {
                "key": key,
                "name": info["name"],
                "standards": info["standards"],
                "categories": info["categories"],
            }
        )
    return {"languages": languages}


# ─────────────────────────────────────────────────────────────
# Repo files (file tree for the editor)
# ─────────────────────────────────────────────────────────────


@agent_router.post("/repo-files")
def get_repo_files(request: CloneRepoRequest):
    try:
        if request.local_path:
            local = Path(request.local_path)
            if not local.exists() or not local.is_dir():
                raise HTTPException(
                    status_code=400,
                    detail="Local path does not exist or is not a directory.",
                )
            repo_path = str(local.resolve())
        elif request.repo_url:
            branch = request.branch if request.branch else None
            repo_path = clone_repository(request.repo_url, branch=branch)
        else:
            raise HTTPException(
                status_code=400,
                detail="Please provide a GitHub URL or a local directory path.",
            )

        files = load_repo_files_for_editor(repo_path)
        return {
            "repo_path": repo_path,
            "total_files": len(files),
            "files": files,
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# Repo branches
# ─────────────────────────────────────────────────────────────


@agent_router.post("/repo-branches")
def get_repo_branches(request: RepoBranchesRequest):
    try:
        if not request.repo_url.strip():
            raise HTTPException(
                status_code=400, detail="Repository URL is required."
            )
        branches = list_remote_branches(request.repo_url)
        return {"branches": branches, "total": len(branches)}

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# Live analysis
# ─────────────────────────────────────────────────────────────


@agent_router.post("/analyze")
def analyze_code_endpoint(request: AnalyzeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty.")

    language = request.language.lower()
    if language not in get_supported_languages():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported language: {language}. "
                f"Supported: {', '.join(get_supported_languages())}"
            ),
        )

    result = analyze_code(request.code, language)
    return {
        "language": language,
        "violations": result["violations"],
        "summary": result["summary"],
    }


# ─────────────────────────────────────────────────────────────
# Fix all (LLM)
# ─────────────────────────────────────────────────────────────


@agent_router.post("/fix")
def fix_code_endpoint(request: FixAllRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty.")

    language = request.language.lower()
    violations = request.violations
    if not violations:
        analysis = analyze_code(request.code, language)
        violations = analysis.get("violations", [])

    if not violations:
        return {
            "explanation": "No violations found — code is already clean!",
            "fixed_code": request.code,
            "diff": "",
        }

    result = fix_all_violations(request.code, language, violations)
    diff = generate_diff(request.code, result["fixed_code"])
    return {
        "explanation": result["explanation"],
        "fixed_code": result["fixed_code"],
        "diff": diff,
    }


# ─────────────────────────────────────────────────────────────
# Polish (definitive iterative fix)
# ─────────────────────────────────────────────────────────────


@agent_router.post("/polish")
def polish_code_endpoint(request: PolishRequest):
    """
    Iteratively analyse + LLM-fix + (Python only) deterministic-format
    until the code has zero remaining violations or progress stalls.

    Returns the polished code, a unified diff vs. the input, the violations
    that remain after the final pass, and a per-stage history.
    """
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty.")

    language = request.language.lower()
    if language not in get_supported_languages():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported language: {language}. "
                f"Supported: {', '.join(get_supported_languages())}"
            ),
        )

    return polish_code(
        request.code, language, max_passes=max(1, min(request.max_passes, 8))
    )


# ─────────────────────────────────────────────────────────────
# Streaming scan
# ─────────────────────────────────────────────────────────────


@agent_router.post("/scan")
def scan_repo(request: ScanRequest):
    return StreamingResponse(
        stream_scan(repo_url=request.repo_url, local_path=request.local_path),
        media_type="text/plain",
    )


# ─────────────────────────────────────────────────────────────
# Apply linters
# ─────────────────────────────────────────────────────────────


@agent_router.post("/apply-linters")
def apply_linters(request: ApplyLintersRequest):
    try:
        return apply_linters_to_repo(request.repo_path)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# Download zipped corrected repo
# ─────────────────────────────────────────────────────────────


@agent_router.get("/download-fixed")
def download_fixed(repo_path: str):
    try:
        repo = Path(repo_path)
        if not repo.exists() or not repo.is_dir():
            raise ValueError("Repository path does not exist.")

        zip_dir = tempfile.mkdtemp()
        repo_name = repo.name or "corrected-repo"
        zip_path = Path(zip_dir) / repo_name

        archive_path = shutil.make_archive(
            str(zip_path), "zip", root_dir=str(repo), base_dir="."
        )
        return FileResponse(
            path=archive_path,
            media_type="application/zip",
            filename=f"{repo_name}-fixed.zip",
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# Get all corrected file contents (for in-browser display)
# ─────────────────────────────────────────────────────────────


@agent_router.get("/corrected-files")
def get_corrected_files(repo_path: str):
    try:
        repo = Path(repo_path)
        if not repo.exists() or not repo.is_dir():
            raise ValueError("Repository path does not exist.")

        files = {}
        supported_exts = get_all_supported_extensions()

        for root, dirs, filenames in os.walk(repo):
            dirs[:] = [
                d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS
            ]
            for fname in sorted(filenames):
                fpath = Path(root) / fname
                if fpath.suffix.lower() not in supported_exts:
                    continue
                rel = str(fpath.relative_to(repo))
                try:
                    files[rel] = fpath.read_text(errors="replace")
                except Exception:
                    files[rel] = "# Could not read file"

        return {"files": files}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# HITL — chat-style assistant
# ─────────────────────────────────────────────────────────────


@agent_router.post(
    "/session",
    response_model=CreateSessionResponse,
    summary="Create a HITL chat session for a code blob",
)
async def create_session(payload: CreateSessionRequest, request: Request):
    if not payload.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty.")
    base_http = str(request.base_url).rstrip("/")
    base_ws = base_http.replace("http://", "ws://").replace("https://", "wss://")
    return await _orchestrator.create_session(payload, base_url=base_ws)


@agent_router.get("/session/{session_id}")
async def get_session(session_id: str):
    session = await _orchestrator.get_session_data(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session.model_dump(mode="json")


@agent_router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    return await _orchestrator.close_session(session_id)


@agent_router.post("/session/{session_id}/approve")
async def approve_session(session_id: str, payload: ApprovalResponse):
    """REST fallback for clients that can't / won't use the WebSocket."""
    return await _orchestrator.handle_rest_approval(session_id, payload)


@agent_router.websocket("/chat/{session_id}")
async def chat_ws(websocket: WebSocket, session_id: str):
    """Live HITL chat channel."""
    await _orchestrator.connect(websocket, session_id)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # Send back an error frame and keep the loop alive.
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "session_id": session_id,
                            "payload": {"text": "Invalid JSON frame."},
                        }
                    )
                )
                continue

            await _orchestrator.handle_message(session_id, data)

    except WebSocketDisconnect:
        await _orchestrator.disconnect(session_id)
    except Exception as exc:
        try:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "session_id": session_id,
                        "payload": {"text": f"Internal error: {exc}"},
                    }
                )
            )
        except Exception:
            pass
        await _orchestrator.disconnect(session_id)
