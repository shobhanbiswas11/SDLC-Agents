"""
api.py — FastAPI server for the Code Refactoring Agent (LangGraph edition).

Replaces worker.py + the Temporal server entirely.
No separate worker process or server daemon needed — just run:

    python api.py
    # or
    uvicorn api:app --reload --port 18200

Endpoints mirror the original Temporal-based API so the existing frontend
(apps/Documentation Drafting agent) works without changes.

Sessions are identified by a thread_id (UUID). LangGraph persists each
session's state (conversation history, workspace path, etc.) in checkpoints.db
using SQLite — completely free and local.

ask_user flow:
    POST /sessions/{id}/message  → graph runs and hits interrupt() → returns
                                   waiting_for_user=true + the question
    POST /sessions/{id}/answer   → resumes the graph with the user's answer
"""

from __future__ import annotations

import os
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from pydantic import BaseModel

load_dotenv()

from agent_node import _augment_message_with_github_paths
from graph import SYSTEM_PROMPT, graph

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Code Refactor Agent — LangGraph",
    description="AI-powered code refactoring agent. No Temporal server required.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session registry (lightweight metadata only) ────────────────────
# Full conversation state is stored in checkpoints.db by LangGraph.
_sessions: dict[str, dict] = {}


# ── Request / Response models ─────────────────────────────────────────────────

class CreateSessionBody(BaseModel):
    workspace_path: str = "."


class MessageBody(BaseModel):
    message: str
    workspace_path: Optional[str] = None


class AnswerBody(BaseModel):
    answer: str


# ── Helper ────────────────────────────────────────────────────────────────────

def _langgraph_config(session_id: str) -> dict:
    """Return LangGraph config dict for a given session (thread)."""
    return {"configurable": {"thread_id": session_id}}


def _sync_session_from_result(session_id: str, result: dict) -> None:
    """Copy agent state fields from a LangGraph result into the session registry."""
    s = _sessions[session_id]
    s["status"]         = result.get("status", "idle")
    s["last_response"]  = result.get("last_response", "")
    s["navigated_file"] = result.get("navigated_file", "")
    s["created_files"]  = result.get("created_files", [])


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/sessions", summary="Create a new refactoring session")
async def create_session(body: CreateSessionBody):
    """
    Start a new agent session for a given workspace.
    Returns a session_id (UUID) to use in all subsequent requests.
    """
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "workspace_path":       body.workspace_path,
        "status":               "idle",
        "last_response":        "",
        "navigated_file":       "",
        "created_files":        [],
        "interrupted_question": None,
    }
    return {"session_id": session_id, "status": "created"}


@app.get("/sessions/{session_id}/status", summary="Poll agent status")
async def get_status(session_id: str):
    """
    Get the current status of a session.
    Frontend polls this to detect when ask_user has paused the agent.
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    s = _sessions[session_id]
    return {
        "session_id":           session_id,
        "status":               s["status"],
        "last_response":        s["last_response"],
        "waiting_for_user":     s["status"] == "waiting_for_user",
        "interrupted_question": s.get("interrupted_question"),
        "navigated_file":       s["navigated_file"],
        "created_files":        s["created_files"],
        "workspace_path":       s["workspace_path"],
        "is_github_backed":     ".refactor_repos" in s["workspace_path"],
    }


@app.post("/sessions/{session_id}/message", summary="Send a message to the agent")
async def send_message(session_id: str, body: MessageBody):
    """
    Send a user message to the agent.

    The agent runs its full ReAct loop (think → tool → observe → ...)
    until it either:
      - Returns a final text answer  → status="idle"
      - Hits ask_user interrupt()    → status="waiting_for_user"
        (frontend must POST /answer to resume)
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    s = _sessions[session_id]
    workspace_path = body.workspace_path or s["workspace_path"]
    s["workspace_path"] = workspace_path
    s["status"] = "thinking"

    # Augment GitHub URLs with path hints
    augmented_message = _augment_message_with_github_paths(body.message, workspace_path)

    config = _langgraph_config(session_id)

    # Check if a previous conversation exists for this thread
    existing = graph.get_state(config)

    if existing and existing.values:
        # Continuing an existing conversation — append the new user message
        prev_history = existing.values.get("history", [])
        new_history  = prev_history + [{"role": "user", "content": augmented_message}]
        input_state  = {**existing.values, "history": new_history, "workspace_path": workspace_path}
    else:
        # New conversation — initialise full state
        input_state = {
            "history": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": augmented_message},
            ],
            "workspace_path":       workspace_path,
            "last_response":        "",
            "status":               "thinking",
            "navigated_file":       "",
            "created_files":        [],
            "pending_tool_calls":   [],
        }

    try:
        result = await graph.ainvoke(input_state, config=config)
    except Exception as exc:
        # Check if the graph paused due to an interrupt (ask_user)
        state_after = graph.get_state(config)
        if state_after and state_after.tasks:
            for task in state_after.tasks:
                if task.interrupts:
                    question = task.interrupts[0].value
                    s["status"]               = "waiting_for_user"
                    s["interrupted_question"] = question
                    s["last_response"]        = f"❓ {question}"
                    return {
                        "session_id":       session_id,
                        "status":           "waiting_for_user",
                        "response":         f"❓ {question}",
                        "waiting_for_user": True,
                        "question":         question,
                    }
        # Real error
        s["status"] = "idle"
        raise HTTPException(status_code=500, detail=str(exc))

    # Check for interrupt in the returned state (alternate path)
    state_after = graph.get_state(config)
    if state_after and state_after.tasks:
        for task in state_after.tasks:
            if task.interrupts:
                question = task.interrupts[0].value
                s["status"]               = "waiting_for_user"
                s["interrupted_question"] = question
                s["last_response"]        = f"❓ {question}"
                return {
                    "session_id":       session_id,
                    "status":           "waiting_for_user",
                    "response":         f"❓ {question}",
                    "waiting_for_user": True,
                    "question":         question,
                }

    _sync_session_from_result(session_id, result)

    return {
        "session_id":     session_id,
        "status":         s["status"],
        "response":       s["last_response"],
        "navigated_file": s["navigated_file"],
        "created_files":  s["created_files"],
    }


@app.post("/sessions/{session_id}/answer", summary="Resume agent after ask_user")
async def answer_user_question(session_id: str, body: AnswerBody):
    """
    Resume a session that was paused by the ask_user tool.

    Call this after the frontend receives waiting_for_user=true.
    The agent will continue from exactly where it stopped.
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    s = _sessions[session_id]
    s["status"]               = "thinking"
    s["interrupted_question"] = None

    config = _langgraph_config(session_id)

    try:
        # Command(resume=answer) tells LangGraph to continue after the interrupt
        result = await graph.ainvoke(Command(resume=body.answer), config=config)
    except Exception as exc:
        # Check for a nested interrupt (e.g. multiple ask_user calls in one run)
        state_after = graph.get_state(config)
        if state_after and state_after.tasks:
            for task in state_after.tasks:
                if task.interrupts:
                    question = task.interrupts[0].value
                    s["status"]               = "waiting_for_user"
                    s["interrupted_question"] = question
                    s["last_response"]        = f"❓ {question}"
                    return {
                        "session_id":       session_id,
                        "status":           "waiting_for_user",
                        "response":         f"❓ {question}",
                        "waiting_for_user": True,
                        "question":         question,
                    }
        s["status"] = "idle"
        raise HTTPException(status_code=500, detail=str(exc))

    _sync_session_from_result(session_id, result)

    return {
        "session_id": session_id,
        "status":     s["status"],
        "response":   s["last_response"],
    }


@app.delete("/sessions/{session_id}", summary="Stop and remove a session")
async def stop_session(session_id: str):
    """Remove a session from the registry. SQLite checkpoint is retained."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    del _sessions[session_id]
    return {"session_id": session_id, "status": "stopped"}


@app.get("/health", summary="Health check")
async def health():
    return {"status": "ok", "engine": "langgraph", "version": "2.0.0"}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "18200"))
    print()
    print("🚀  Code Refactor Agent — LangGraph Edition")
    print(f"    Server: http://localhost:{port}")
    print("    Docs:   http://localhost:{port}/docs")
    print()
    print("    ✅  No Temporal server needed")
    print("    ✅  State persisted to checkpoints.db (SQLite)")
    print()

    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
