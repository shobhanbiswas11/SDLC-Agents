"""
app/api.py — FastAPI server for the Code Refactoring Agent (LangGraph edition).

Run with:
    uvicorn app.api:app --reload --port 18200

Key improvements over the original api.py:
  - Graph compiled ONCE at startup via FastAPI lifespan (not per-request).
  - AsyncSqliteSaver context managed through the full app lifetime.
  - Duplicate interrupt-detection blocks consolidated into _check_for_interrupt().
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from pydantic import BaseModel

load_dotenv()

from agent.graph import build_graph
from agent.utils.github_utils import augment_message_with_github_paths
from core.config_loader import load_all_config
from core.logging import get_logger

logger = get_logger(__name__)

_graph = None
CHECKPOINT_DB = os.getenv("CHECKPOINT_DB_PATH", "checkpoints.db")
SYSTEM_PROMPT, _, _ = load_all_config()
_DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://localhost:3001,http://localhost:8002,http://localhost:18200"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    logger.info("Compiling graph with AsyncSqliteSaver → %s", CHECKPOINT_DB)
    async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB) as memory:
        _graph = build_graph().compile(checkpointer=memory)
        logger.info("Graph ready ✓")
        yield
    logger.info("SQLite connection closed")


app = FastAPI(
    title="Code Refactor Agent — LangGraph",
    description="AI-powered code refactoring agent. No Temporal server required.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: dict[str, dict] = {}


class CreateSessionBody(BaseModel):
    workspace_path: str = "."
    source_type: Optional[str] = "local"
    github_url: Optional[str] = None
    github_branch: Optional[str] = "main"
    access_token: Optional[str] = None


class MessageBody(BaseModel):
    message: str
    workspace_path: Optional[str] = None


class AnswerBody(BaseModel):
    answer: str


def _lg_config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


def _require_session(session_id: str) -> dict:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return _sessions[session_id]


async def _require_or_recover_session(session_id: str) -> dict:
    """
    Return session metadata, rebuilding it from the LangGraph checkpoint after
    a dev-server reload. Uvicorn --reload clears the in-memory _sessions map.
    """
    if session_id in _sessions:
        return _sessions[session_id]

    state = await _graph.aget_state(_lg_config(session_id))
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Session not found")

    values = state.values
    _sessions[session_id] = {
        "workspace_path": values.get("workspace_path", "."),
        "repo_url": values.get("repo_url", ""),
        "github_branch": values.get("github_branch", "main"),
        "github_token": values.get("github_token", ""),
        "status": values.get("status", "idle"),
        "last_response": values.get("last_response", ""),
        "navigated_file": values.get("navigated_file", ""),
        "created_files": values.get("created_files", []),
        "interrupted_question": None,
    }
    logger.info("Recovered session from checkpoint: %s", session_id)
    return _sessions[session_id]


async def _check_for_interrupt(session_id: str, s: dict) -> dict | None:
    state_after = await _graph.aget_state(_lg_config(session_id))
    if state_after and state_after.tasks:
        for task in state_after.tasks:
            if task.interrupts:
                question = task.interrupts[0].value
                s["status"] = "waiting_for_user"
                s["interrupted_question"] = question
                s["last_response"] = f"❓ {question}"
                return {
                    "session_id": session_id,
                    "status": "waiting_for_user",
                    "response": f"❓ {question}",
                    "waiting_for_user": True,
                    "question": question,
                }
    return None


def _sync_session(session_id: str, result: dict) -> None:
    s = _sessions[session_id]
    s["status"] = result.get("status", "idle")
    s["last_response"] = result.get("last_response", "")
    s["navigated_file"] = result.get("navigated_file", "")
    s["created_files"] = result.get("created_files", [])
    s["workspace_path"] = result.get("workspace_path", s.get("workspace_path", "."))
    s["repo_url"] = result.get("repo_url", s.get("repo_url", ""))
    s["github_branch"] = result.get("github_branch", s.get("github_branch", "main"))
    s["interrupted_question"] = None


@app.post("/sessions", summary="Create a new refactoring session")
async def create_session(body: CreateSessionBody):
    session_id = str(uuid.uuid4())
    repo_url = body.github_url or ""
    source_type = (body.source_type or "local").lower()
    if source_type == "local" and not body.github_url:
        repo_url = ""
    _sessions[session_id] = {
        "workspace_path": body.workspace_path,
        "repo_url": repo_url,
        "github_branch": body.github_branch or "main",
        "github_token": body.access_token or "",
        "status": "idle",
        "last_response": "",
        "navigated_file": "",
        "created_files": [],
        "interrupted_question": None,
    }
    logger.info("Session created: %s", session_id)
    return {"session_id": session_id, "status": "created"}


@app.get("/sessions/{session_id}/status", summary="Poll agent status")
async def get_status(session_id: str):
    s = await _require_or_recover_session(session_id)
    return {
        "session_id": session_id,
        "status": s["status"],
        "last_response": s["last_response"],
        "waiting_for_user": s["status"] == "waiting_for_user",
        "interrupted_question": s.get("interrupted_question"),
        "navigated_file": s["navigated_file"],
        "created_files": s["created_files"],
        "workspace_path": s["workspace_path"],
        "is_github_backed": bool(s.get("repo_url")) or ".refactor_repos" in s["workspace_path"],
    }


@app.post("/sessions/{session_id}/message", summary="Send a message to the agent")
async def send_message(session_id: str, body: MessageBody):
    s = await _require_or_recover_session(session_id)
    workspace_path = body.workspace_path or s["workspace_path"]
    s["workspace_path"] = workspace_path
    s["status"] = "thinking"

    augmented = augment_message_with_github_paths(body.message, workspace_path)
    config = _lg_config(session_id)
    existing = await _graph.aget_state(config)

    if existing and existing.values:
        input_state = {
            **existing.values,
            "history": existing.values.get("history", []) + [{"role": "user", "content": augmented}],
            "workspace_path": workspace_path,
            "verification_passed": False,
            "verification_attempts": 0,
            "finalize_after_tool": False,
        }
        for key in ("repo_url", "github_token", "github_branch"):
            if s.get(key) and not input_state.get(key):
                input_state[key] = s[key]
    else:
        input_state = {
            "history": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": augmented},
            ],
            "workspace_path": workspace_path,
            "repo_url": s.get("repo_url", ""),
            "github_branch": s.get("github_branch", "main"),
            "github_token": s.get("github_token", ""),
            "last_response": "",
            "status": "thinking",
            "navigated_file": "",
            "created_files": [],
            "pending_tool_calls": [],
            "context_gathered": False,
            "verification_passed": False,
            "verification_attempts": 0,
            "finalize_after_tool": False,
        }

    try:
        result = await _graph.ainvoke(input_state, config=config)
    except Exception:
        interrupt_resp = await _check_for_interrupt(session_id, s)
        if interrupt_resp:
            return interrupt_resp
        s["status"] = "idle"
        raise HTTPException(status_code=500, detail="Agent encountered an unexpected error.")

    interrupt_resp = await _check_for_interrupt(session_id, s)
    if interrupt_resp:
        return interrupt_resp

    _sync_session(session_id, result)
    return {
        "session_id": session_id,
        "status": s["status"],
        "response": s["last_response"],
        "navigated_file": s["navigated_file"],
        "created_files": s["created_files"],
    }


@app.post("/sessions/{session_id}/answer", summary="Resume agent after ask_user")
async def answer_user_question(session_id: str, body: AnswerBody):
    s = await _require_or_recover_session(session_id)
    s["status"] = "thinking"
    s["interrupted_question"] = None
    config = _lg_config(session_id)

    try:
        result = await _graph.ainvoke(Command(resume=body.answer), config=config)
    except Exception:
        interrupt_resp = await _check_for_interrupt(session_id, s)
        if interrupt_resp:
            return interrupt_resp
        s["status"] = "idle"
        raise HTTPException(status_code=500, detail="Agent encountered an unexpected error.")

    interrupt_resp = await _check_for_interrupt(session_id, s)
    if interrupt_resp:
        return interrupt_resp

    _sync_session(session_id, result)
    return {"session_id": session_id, "status": s["status"], "response": s["last_response"]}


@app.delete("/sessions/{session_id}", summary="Stop and remove a session")
async def stop_session(session_id: str):
    _require_session(session_id)
    del _sessions[session_id]
    return {"session_id": session_id, "status": "stopped"}


@app.get("/health", summary="Health check")
async def health():
    return {"status": "ok", "engine": "langgraph", "version": "2.1.0"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "18200"))
    uvicorn.run("app.api:app", host="0.0.0.0", port=port, reload=True)
