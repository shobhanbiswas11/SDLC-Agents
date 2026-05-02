"""
api.py — FastAPI server for the Documentation Drafting Agent (LangGraph edition).

Replaces worker.py + the Temporal server entirely.
No separate worker process or server daemon needed — just run:

    python api.py
    # or
    uvicorn api:app --reload --port 8002

Endpoints:
  Agent session (LangGraph-backed, multi-turn, stateful):
    POST   /sessions              → create a new session
    GET    /sessions/{id}/status  → poll agent status
    POST   /sessions/{id}/message → send a user message
    POST   /sessions/{id}/answer  → resume after ask_user pause
    DELETE /sessions/{id}         → stop and remove a session

  Direct RAG chat (no memory, one-shot):
    POST   /chat         → one-shot RAG answer
    POST   /stream-chat  → same but streamed as Server-Sent Events

  Legacy-compat aliases (for existing frontend):
    POST   /api/workflows                          → create session
    GET    /api/workflows/{id}/status              → poll status
    POST   /api/workflows/{id}/messages            → send message
    DELETE /api/workflows/{id}                     → stop session

  Utility:
    GET    /api/agents → list available agents
    GET    /health     → health check
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from agent_node import _get_sync_openai_client
from config_loader import load_agent_config, load_all_config
from graph import SYSTEM_PROMPT, graph

# ── RAG pipeline modules (for /chat and /stream-chat) ────────────────────────
from parsers.tree_fetcher        import fetch_full_repo, fetch_local_repo
from parsers.ast_graph_builder   import build_combined_graph
from parsers.metadata_extractor  import format_metadata_block, extract_all_metadata
from intelligence.file_ranker    import rank_files
from intelligence.semantic_ranker import semantic_rerank
from intelligence.context_selector import select_snippets
from intelligence.chat_prompt    import build_chat_prompt

_GLOBAL_EMBEDDING_CACHE: dict = {}

# ── Session persistence ───────────────────────────────────────────────────────
_SESSIONS_FILE = Path(__file__).parent / "sessions.json"


def _load_sessions() -> dict:
    """Load sessions from disk on startup."""
    try:
        if _SESSIONS_FILE.exists():
            data = json.loads(_SESSIONS_FILE.read_text(encoding="utf-8"))
            print(f"[sessions] Restored {len(data)} session(s) from disk.")
            return data
    except Exception as e:
        print(f"[sessions] Could not restore sessions: {e}")
    return {}


def _save_sessions(sessions: dict) -> None:
    """Persist sessions to disk (writes only serialisable fields)."""
    try:
        safe = {
            sid: {
                "workspace_path":       s.get("workspace_path", "."),
                "repo_url":             s.get("repo_url", ""),
                "github_token":         s.get("github_token", ""),
                "status":               s.get("status", "idle"),
                "last_response":        s.get("last_response", ""),
                "navigated_file":       s.get("navigated_file", ""),
                "created_files":        s.get("created_files", []),
                "interrupted_question": s.get("interrupted_question"),
            }
            for sid, s in sessions.items()
        }
        _SESSIONS_FILE.write_text(json.dumps(safe, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[sessions] Could not persist sessions: {e}")


# ── App setup ─────────────────────────────────────────────────────────────────

# Rate limiter — 60 requests/minute per IP globally
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="Documentation Drafting Agent — LangGraph",
    description="AI-powered documentation agent. No Temporal server required.",
    version="2.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://localhost:13100")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session registry (pre-loaded from disk) ─────────────────────────
_sessions: dict[str, dict] = _load_sessions()



# ── Request / Response models ─────────────────────────────────────────────────

class CreateSessionBody(BaseModel):
    agent_id:       str = "reviewer"
    workspace_path: str = "."
    repo:           Optional[str] = None
    access_token:   Optional[str] = None


class MessageBody(BaseModel):
    message:        str
    workspace_path: Optional[str] = None


class AnswerBody(BaseModel):
    answer: str


class ChatRequest(BaseModel):
    repo:         str = ""
    access_token: str = ""
    local_path:   Optional[str] = None
    message:      str


class ChatResponse(BaseModel):
    answer:        str
    context_files: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _langgraph_config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


def _sync_session_from_result(session_id: str, result: dict) -> None:
    s = _sessions[session_id]
    s["status"]         = result.get("status", "idle")
    s["last_response"]  = result.get("last_response", "")
    s["navigated_file"] = result.get("navigated_file", "")
    s["created_files"]  = result.get("created_files", [])


def _normalize_repo_identifier(repo_value: str) -> str:
    raw = (repo_value or "").strip()
    if not raw:
        raise ValueError("repo cannot be empty")
    for pattern in [
        r"^https?://(?:www\.)?github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)",
        r"^(?:www\.)?github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)",
    ]:
        m = re.match(pattern, raw)
        if m:
            owner, repo = m.group("owner").strip(), m.group("repo").strip()
            if repo.endswith(".git"):
                repo = repo[:-4]
            if owner and repo:
                return f"{owner}/{repo}"
    parts = [p for p in raw.split("/") if p]
    if len(parts) >= 2:
        owner, repo = parts[0].strip(), parts[1].strip()
        if repo.endswith(".git"):
            repo = repo[:-4]
        if owner and repo:
            return f"{owner}/{repo}"
    raise ValueError("repo should be 'owner/repo' or a GitHub URL")


# ── Utility Endpoints ─────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "message": "Documentation Drafting Agent — LangGraph Edition"}


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "langgraph", "version": "2.0.0"}


@app.get("/api/agents")
async def list_agents() -> Dict[str, Any]:
    agent_config = load_agent_config()
    return {
        "agents": [{
            "id":          agent_config.get("id", "reviewer"),
            "name":        agent_config.get("name", "Documentation Agent"),
            "description": agent_config.get("description", ""),
            "tools":       agent_config.get("tools", []),
        }]
    }


# ── Session Endpoints (LangGraph-backed) ──────────────────────────────────────

@app.post("/sessions", summary="Create a new documentation session")
@limiter.limit("20/minute")
async def create_session(request: Request, body: CreateSessionBody):
    session_id = str(uuid.uuid4())
    
    # Pre-normalize the repo URL if it was provided
    normalized_repo = ""
    if body.repo:
        try:
            normalized_repo = _normalize_repo_identifier(body.repo)
        except ValueError:
            pass
            
    _sessions[session_id] = {
        "workspace_path":       body.workspace_path,
        "repo_url":             normalized_repo,
        "github_token":         body.access_token or "",
        "status":               "idle",
        "last_response":        "",
        "navigated_file":       "",
        "created_files":        [],
        "interrupted_question": None,
    }
    _save_sessions(_sessions)
    return {"session_id": session_id, "status": "created"}


@app.get("/sessions/{session_id}/status", summary="Poll agent status")
async def get_status(session_id: str):
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
    }


@app.post("/sessions/{session_id}/message", summary="Send a message to the agent")
async def send_message(session_id: str, body: MessageBody):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    s              = _sessions[session_id]
    workspace_path = body.workspace_path or s["workspace_path"]
    s["workspace_path"] = workspace_path
    s["status"]    = "thinking"

    config = _langgraph_config(session_id)

    existing = graph.get_state(config)
    if existing and existing.values:
        prev_history = existing.values.get("history", [])
        new_history  = prev_history + [{"role": "user", "content": body.message}]
        input_state  = {
            **existing.values, 
            "history": new_history, 
            "workspace_path": workspace_path
        }
        if s.get("repo_url") and not input_state.get("repo_url"):
            input_state["repo_url"] = s["repo_url"]
        if s.get("github_token") and not input_state.get("github_token"):
            input_state["github_token"] = s["github_token"]
    else:
        input_state = {
            "history": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": body.message},
            ],
            "workspace_path":     workspace_path,
            "repo_url":           s.get("repo_url", ""),
            "github_token":       s.get("github_token", ""),
            "last_response":      "",
            "status":             "thinking",
            "navigated_file":     "",
            "created_files":      [],
            "pending_tool_calls": [],
            "context_gathered":   False,
        }

    try:
        result = await graph.ainvoke(input_state, config=config)
    except Exception as exc:
        state_after = graph.get_state(config)
        if state_after and state_after.tasks:
            for task in state_after.tasks:
                if task.interrupts:
                    question               = task.interrupts[0].value
                    s["status"]            = "waiting_for_user"
                    s["interrupted_question"] = question
                    s["last_response"]     = f"❓ {question}"
                    return {
                        "session_id":       session_id,
                        "status":           "waiting_for_user",
                        "response":         f"❓ {question}",
                        "waiting_for_user": True,
                        "question":         question,
                    }
        s["status"] = "idle"
        raise HTTPException(status_code=500, detail=str(exc))

    # Check for interrupt in the returned state
    state_after = graph.get_state(config)
    if state_after and state_after.tasks:
        for task in state_after.tasks:
            if task.interrupts:
                question               = task.interrupts[0].value
                s["status"]            = "waiting_for_user"
                s["interrupted_question"] = question
                s["last_response"]     = f"❓ {question}"
                return {
                    "session_id":       session_id,
                    "status":           "waiting_for_user",
                    "response":         f"❓ {question}",
                    "waiting_for_user": True,
                    "question":         question,
                }

    _sync_session_from_result(session_id, result)
    _save_sessions(_sessions)
    return {
        "session_id":     session_id,
        "status":         s["status"],
        "response":       s["last_response"],
        "navigated_file": s["navigated_file"],
        "created_files":  s["created_files"],
    }


@app.post("/sessions/{session_id}/answer", summary="Resume agent after ask_user")
async def answer_user_question(session_id: str, body: AnswerBody):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    s                         = _sessions[session_id]
    s["status"]               = "thinking"
    s["interrupted_question"] = None

    config = _langgraph_config(session_id)

    try:
        result = await graph.ainvoke(Command(resume=body.answer), config=config)
    except Exception as exc:
        state_after = graph.get_state(config)
        if state_after and state_after.tasks:
            for task in state_after.tasks:
                if task.interrupts:
                    question               = task.interrupts[0].value
                    s["status"]            = "waiting_for_user"
                    s["interrupted_question"] = question
                    s["last_response"]     = f"❓ {question}"
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
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    del _sessions[session_id]
    return {"session_id": session_id, "status": "stopped"}


# ── Legacy Alias Endpoints (keeps frontend working unchanged) ─────────────────

@app.post("/api/workflows")
async def legacy_start_workflow(body: CreateSessionBody):
    result = await create_session(body)
    # Return as workflow_id for backward compat with existing frontend
    return {"workflow_id": result["session_id"]}


@app.post("/api/workflows/{workflow_id}/messages")
async def legacy_send_message(workflow_id: str, body: MessageBody):
    result = await send_message(workflow_id, body)
    return {"status": "message_sent"}


@app.get("/api/workflows/{workflow_id}/status")
async def legacy_get_status(workflow_id: str):
    if workflow_id not in _sessions:
        return {
            "status": {
                "status":           "waiting_for_worker",
                "last_response":    "",
                "waiting_for_user": False,
                "message_count":    0,
            }
        }
    s = _sessions[workflow_id]
    return {
        "status": {
            "status":           s["status"],
            "last_response":    s["last_response"],
            "waiting_for_user": s["status"] == "waiting_for_user",
            "pending_question": s.get("interrupted_question"),
            "message_count":    len(graph.get_state(_langgraph_config(workflow_id)).values.get("history", [])) if graph.get_state(_langgraph_config(workflow_id)) else 0,
        }
    }


@app.delete("/api/workflows/{workflow_id}")
async def legacy_stop_workflow(workflow_id: str):
    return await stop_session(workflow_id)


# ── Direct RAG Chat Endpoints (no memory, one-shot) ───────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest):
    """
    One-shot RAG-powered chat. For conversational multi-turn chat, use /sessions.
    """
    if body.local_path:
        target_name     = body.local_path
        normalized_repo = ""
        token           = ""
    else:
        token = body.access_token or os.environ.get("YOUR_GITHUB_ACCESS_TOKEN", "")
        if not token:
            raise HTTPException(status_code=400, detail="GitHub access token required for remote repositories")
        try:
            normalized_repo = _normalize_repo_identifier(body.repo)
        except ValueError:
            raise HTTPException(status_code=400, detail="repo should be 'owner/repo' or a GitHub URL")
        target_name = normalized_repo

    try:
        if body.local_path:
            file_map, file_tree = fetch_local_repo(body.local_path)
        else:
            file_map, file_tree = fetch_full_repo(normalized_repo, token, branch="main")

        if not file_tree:
            raise HTTPException(status_code=404, detail="No documents found to parse.")

        metadata        = extract_all_metadata(file_map)
        metadata_block  = format_metadata_block(metadata)
        structure       = "\n".join([f"Repository: {target_name}"] + file_tree)
        graph_map       = build_combined_graph(file_map)
        ranked          = rank_files(file_map, file_tree, graph_map, top_k=40, include_all=False)

        azure_client       = _get_sync_openai_client()
        embedding_dep      = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
        use_semantic       = os.getenv("USE_SEMANTIC_RANKING", "true").lower() in ("1", "true", "yes")

        if use_semantic:
            try:
                emb_dep = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-2")
                ranked = semantic_rerank(
                    ranked[:40], file_map, model=emb_dep,
                    query=body.message, top_k=15, cached_embeddings=_GLOBAL_EMBEDDING_CACHE,
                )
            except Exception as e:
                print(f"Semantic reranking failed, falling back: {e}")
                ranked = ranked[:15]
        else:
            ranked = ranked[:15]

        context_files  = [p for p, _ in ranked]
        code_snippets  = select_snippets(file_map, ranked, max_chars=16000, lines_per_file=150)
        prompt         = build_chat_prompt(structure, metadata_block, code_snippets, body.message)
        chat_dep       = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

        response = azure_client.chat.completions.create(
            model=chat_dep,
            messages=[
                {"role": "system", "content": "You are a helpful AI code assistant specialized in documentation. Output your responses directly in raw Markdown. NEVER wrap your entire response in a markdown code fence (```markdown ... ```). Only use code fences for actual code snippets."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        return ChatResponse(
            answer=response.choices[0].message.content.strip(),
            context_files=context_files,
        )

    except Exception as e:
        print(f"Error in /chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream-chat")
async def stream_chat_endpoint(body: ChatRequest):
    """Streaming SSE version of /chat."""
    if body.local_path:
        target_name     = body.local_path
        normalized_repo = ""
        token           = ""
    else:
        token = body.access_token or os.environ.get("YOUR_GITHUB_ACCESS_TOKEN", "")
        if not token:
            raise HTTPException(status_code=400, detail="GitHub access token required")
        try:
            normalized_repo = _normalize_repo_identifier(body.repo)
        except ValueError:
            raise HTTPException(status_code=400, detail="repo should be 'owner/repo' or a GitHub URL")
        target_name = normalized_repo

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching code context...'})}\n\n"

            if body.local_path:
                file_map, file_tree = fetch_local_repo(body.local_path)
            else:
                file_map, file_tree = fetch_full_repo(normalized_repo, token, branch="main")

            if not file_tree:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No documents found.'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing codebase and ranking files...'})}\n\n"
            await asyncio.sleep(0.05)

            metadata       = extract_all_metadata(file_map)
            metadata_block = format_metadata_block(metadata)
            structure      = "\n".join([f"Repository: {target_name}"] + file_tree)

            graph_map = await asyncio.to_thread(build_combined_graph, file_map)
            ranked    = await asyncio.to_thread(rank_files, file_map, file_tree, graph_map, 40, False)

            azure_client  = _get_sync_openai_client()
            embedding_dep = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
            use_semantic  = os.getenv("USE_SEMANTIC_RANKING", "true").lower() in ("1", "true", "yes")

            if use_semantic:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Performing semantic intelligence ranking...'})}\n\n"
                try:
                    emb_dep = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-2")
                    ranked = semantic_rerank(
                        ranked[:40], file_map, model=emb_dep,
                        query=body.message, top_k=15, cached_embeddings=_GLOBAL_EMBEDDING_CACHE,
                    )
                except Exception as e:
                    print(f"Semantic reranking failed: {e}")
                    ranked = ranked[:15]
            else:
                ranked = ranked[:15]

            context_files = [p for p, _ in ranked]
            code_snippets = select_snippets(file_map, ranked, max_chars=16000, lines_per_file=150)
            prompt        = build_chat_prompt(structure, metadata_block, code_snippets, body.message)

            yield f"data: {json.dumps({'type': 'status', 'message': 'Consulting AI model...'})}\n\n"

            chat_dep = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
            response = azure_client.chat.completions.create(
                model=chat_dep,
                messages=[
                    {"role": "system", "content": "You are a helpful AI code assistant specialized in documentation. Output your responses directly in raw Markdown."},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.2,
                max_tokens=4000,
                stream=True,
            )

            _sentinel     = object()
            response_iter = iter(response)
            while True:
                chunk = await asyncio.to_thread(next, response_iter, _sentinel)
                if chunk is _sentinel:
                    break
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield f"data: {json.dumps({'type': 'chunk', 'content': delta.content})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'context_files': context_files})}\n\n"

        except Exception as e:
            print(f"Error in /stream-chat: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection":    "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8002))
    print()
    print("🚀  Documentation Drafting Agent — LangGraph Edition")
    print(f"    Server:  http://localhost:{port}")
    print(f"    Docs:    http://localhost:{port}/docs")
    print()
    print("    ✅  No Temporal server needed")
    print("    ✅  State persisted to checkpoints.db (SQLite)")
    print()
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
