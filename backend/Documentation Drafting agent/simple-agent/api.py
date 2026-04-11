"""
api.py — FastAPI server.

Exposes HTTP endpoints for:
  1. Temporal agent sessions — what cli.py talks to
     POST   /api/workflows              → start a session
     POST   /api/workflows/{id}/messages → send a message
     GET    /api/workflows/{id}/status   → poll for a response
     DELETE /api/workflows/{id}          → end the session
  2. Direct RAG-powered chat — one-shot (no Temporal, no conversation memory)
     POST   /chat         → answer a question about a repo
     POST   /stream-chat  → same but streamed as Server-Sent Events
"""

import os
import uuid
import asyncio
import json
import re
from datetime import timedelta
from typing import Any, Dict, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from temporalio.client import Client

from workflow import AgentWorkflow, WorkflowInput
from config_loader import load_agent_config

# ── RAG pipeline modules ──────────────────────────────────────────────────────
# parsers/  → scans repo, extracts metadata, builds AST import graph
# intelligence/ → ranks files by relevance, semantic reranking, context slicing
from parsers.tree_fetcher import fetch_full_repo, fetch_local_repo
from parsers.ast_graph_builder import build_combined_graph
from parsers.metadata_extractor import format_metadata_block, extract_all_metadata
from intelligence.file_ranker import rank_files
from intelligence.semantic_ranker import semantic_rerank
from intelligence.context_selector import select_snippets
from intelligence.chat_prompt import build_chat_prompt

_GLOBAL_EMBEDDING_CACHE = {}

# Load .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="Unified Agent API")

_cors_origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://localhost:13100")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TASK_QUEUE = "simple-agent-queue"
TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")
TEMPORAL_NAMESPACE = os.environ.get("TEMPORAL_NAMESPACE", "default")
TEMPORAL_API_KEY = os.environ.get("TEMPORAL_API_KEY")
TEMPORAL_TLS = os.environ.get("TEMPORAL_TLS")


def _resolve_temporal_tls_setting() -> bool | None:
    if not TEMPORAL_TLS or not TEMPORAL_TLS.strip():
        return None
    value = TEMPORAL_TLS.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return None


# --- Single global Temporal client (reused across requests) ---
_temporal_client: Optional[Client] = None


async def get_client() -> Client:
    """Connect to the Temporal server (reuse existing connection if available)."""
    global _temporal_client
    if not _temporal_client:
        try:
            connect_kwargs: Dict[str, Any] = {
                "namespace": TEMPORAL_NAMESPACE,
                "tls": _resolve_temporal_tls_setting(),
            }
            if TEMPORAL_API_KEY and TEMPORAL_API_KEY.strip():
                connect_kwargs["api_key"] = TEMPORAL_API_KEY.strip()
            _temporal_client = await Client.connect(TEMPORAL_ADDRESS, **connect_kwargs)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cannot connect to Temporal: {e}")
    return _temporal_client


def _get_azure_client():
    """
    Build an Azure OpenAI client from environment variables.
    Uses service principal auth (AZURE_TENANT_ID / CLIENT_ID / CLIENT_SECRET) if set,
    otherwise falls back to AZURE_OPENAI_API_KEY.
    """
    from openai import AzureOpenAI
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    tenant_id = os.getenv("AZURE_TENANT_ID", "")
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")

    if tenant_id and client_id and client_secret:
        from azure.identity import ClientSecretCredential
        cred = ClientSecretCredential(tenant_id, client_id, client_secret)
        token = cred.get_token("https://cognitiveservices.azure.com/.default")
        return AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=token.token)

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_version=api_version,
        api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
    )


def _normalize_repo_identifier(repo_value: str) -> str:
    """
    Accept 'owner/repo', 'https://github.com/owner/repo', or 'github.com/owner/repo'
    and return 'owner/repo'.
    """
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

    raise ValueError("repo should be in the format 'owner/repo' or a GitHub repo URL")


# ── Request / Response models ─────────────────────────────────────────────────

class StartRequest(BaseModel):
    agent_id: str = "reviewer"
    workspace_path: str = "."


class MessageRequest(BaseModel):
    message: str


class ChatRequest(BaseModel):
    repo: str = ""
    access_token: str = ""
    local_path: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    answer: str
    context_files: list[str]


# ── Temporal Agent Endpoints ──────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "message": "Unified Agent API is running"}


@app.get("/api/agents")
async def list_agents() -> Dict[str, Any]:
    agent_config = load_agent_config()
    return {
        "agents": [{
            "id": agent_config.get("id", "reviewer"),
            "name": agent_config.get("name", "Universal Agent"),
            "description": agent_config.get("description", "Handles code review, GitHub file operations, documentation, and local file tasks."),
            "tools": agent_config.get("tools", ["github_tool", "read_file", "write_file", "list_files", "ask_user"])
        }]
    }


@app.post("/api/workflows")
async def start_workflow(req: StartRequest) -> Dict[str, str]:
    """Start a new Temporal agent session."""
    client = await get_client()
    workflow_id = f"agent-{uuid.uuid4().hex[:8]}"

    await client.start_workflow(
        AgentWorkflow.run,
        WorkflowInput(agent_id=req.agent_id, workspace_path=req.workspace_path),
        id=workflow_id,
        task_queue=TASK_QUEUE,
        execution_timeout=timedelta(hours=24),
    )

    return {"workflow_id": workflow_id}


@app.post("/api/workflows/{workflow_id}/messages")
async def send_message(workflow_id: str, req: MessageRequest) -> Dict[str, str]:
    """Send a user message into the running workflow via a Temporal signal."""
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        await handle.signal(AgentWorkflow.send_message, req.message)
        return {"status": "message_sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/{workflow_id}/status")
async def get_status(workflow_id: str) -> Dict[str, Any]:
    """Poll the workflow for its current status and last response."""
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        status = await handle.query(AgentWorkflow.get_status)
        return {"status": status}
    except Exception as e:
        # If the worker hasn't started or the workflow is not initialized, catch the exception
        # so that the UI can gracefully show a waiting state instead of a 500 error.
        return {
            "status": {
                "status": "waiting_for_worker",
                "last_response": "",
                "waiting_for_user": False,
                "message_count": 0,
                "error": str(e)
            }
        }


@app.delete("/api/workflows/{workflow_id}")
async def stop_workflow(workflow_id: str) -> Dict[str, str]:
    """Gracefully stop a workflow session."""
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        await handle.signal(AgentWorkflow.stop)
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Direct RAG Chat Endpoints (no Temporal) ───────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest):
    """
    One-shot RAG-powered chat.

    Pipeline:
      1. Fetch repo files (local or GitHub)
      2. Extract metadata (imports, functions, routes, deps)
      3. Build AST import graph
      4. Rank files by structural importance
      5. Semantic rerank top-40 against the user query
      6. Slice relevant code snippets
      7. Build prompt → call Azure OpenAI → return answer

    For conversational multi-turn chat, use the /api/workflows endpoints instead.
    """
    if body.local_path:
        target_name = body.local_path
        normalized_repo = ""
        token = ""
    else:
        token = body.access_token or os.environ.get("YOUR_GITHUB_ACCESS_TOKEN", "")
        if not token:
            raise HTTPException(status_code=400, detail="GitHub access token required for remote repositories")
        try:
            normalized_repo = _normalize_repo_identifier(body.repo)
        except ValueError:
            raise HTTPException(status_code=400, detail="repo should be in the format 'owner/repo' or a GitHub URL")
        target_name = normalized_repo

    try:
        # Step 1: Fetch files
        if body.local_path:
            file_map, file_tree = fetch_local_repo(body.local_path)
        else:
            file_map, file_tree = fetch_full_repo(normalized_repo, token, branch="main")

        if not file_tree:
            raise HTTPException(status_code=404, detail="No documents found to parse.")

        # Step 2: Extract metadata
        metadata = extract_all_metadata(file_map)
        metadata_block = format_metadata_block(metadata)
        structure = "\n".join([f"Repository: {target_name}"] + file_tree)

        # Step 3 + 4: Build graph and rank files by structural importance
        graph = build_combined_graph(file_map)
        ranked = rank_files(file_map, file_tree, graph, top_k=40, include_all=False)

        # Step 5: Semantic rerank against the user query
        azure_client = _get_azure_client()
        embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
        use_semantic = os.getenv("USE_SEMANTIC_RANKING", "true").lower() in ("1", "true", "yes")

        if use_semantic:
            try:
                ranked = semantic_rerank(
                    ranked[:40], file_map, azure_client, embedding_deployment,
                    query=body.message, top_k=15, cached_embeddings=_GLOBAL_EMBEDDING_CACHE
                )
            except Exception as e:
                print(f"Semantic reranking failed, falling back to structural rank: {e}")
                ranked = ranked[:15]
        else:
            ranked = ranked[:15]

        # Step 6 + 7: Slice snippets, build prompt, call LLM
        context_files = [p for p, _ in ranked]
        code_snippets = select_snippets(file_map, ranked, max_chars=16000, lines_per_file=150)
        prompt = build_chat_prompt(structure, metadata_block, code_snippets, body.message)

        chat_deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        response = azure_client.chat.completions.create(
            model=chat_deployment,
            messages=[
                {"role": "system", "content": "You are a helpful and expert AI code assistant specialized in documentation. Output your responses directly in raw Markdown. NEVER wrap your entire response in a markdown code fence (```markdown ... ```). Only use code fences for actual code snippets. When generating documentation, start directly with the heading (e.g., '# Project Name')."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4000,
        )

        return ChatResponse(
            answer=response.choices[0].message.content.strip(),
            context_files=context_files,
        )

    except Exception as e:
        print(f"Error in /chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream-chat")
async def stream_chat_endpoint(body: ChatRequest):
    """
    Streaming SSE version of /chat.
    Sends real-time status updates and AI response chunks as Server-Sent Events.
    """
    if body.local_path:
        target_name = body.local_path
        normalized_repo = ""
        token = ""
    else:
        token = body.access_token or os.environ.get("YOUR_GITHUB_ACCESS_TOKEN", "")
        if not token:
            raise HTTPException(status_code=400, detail="GitHub access token required for remote repositories")
        try:
            normalized_repo = _normalize_repo_identifier(body.repo)
        except ValueError:
            raise HTTPException(status_code=400, detail="repo should be in the format 'owner/repo' or a GitHub URL")
        target_name = normalized_repo

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching code context...'})}\n\n"

            if body.local_path:
                file_map, file_tree = fetch_local_repo(body.local_path)
            else:
                file_map, file_tree = fetch_full_repo(normalized_repo, token, branch="main")

            if not file_tree:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No documents found to parse.'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing codebase and ranking files...'})}\n\n"

            metadata = extract_all_metadata(file_map)
            metadata_block = format_metadata_block(metadata)
            structure = "\n".join([f"Repository: {target_name}"] + file_tree)

            graph = build_combined_graph(file_map)
            ranked = rank_files(file_map, file_tree, graph, top_k=40, include_all=False)

            azure_client = _get_azure_client()
            embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
            use_semantic = os.getenv("USE_SEMANTIC_RANKING", "true").lower() in ("1", "true", "yes")

            if use_semantic:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Performing semantic intelligence ranking...'})}\n\n"
                try:
                    ranked = semantic_rerank(
                        ranked[:40], file_map, azure_client, embedding_deployment,
                        query=body.message, top_k=15, cached_embeddings=_GLOBAL_EMBEDDING_CACHE
                    )
                except Exception as e:
                    print(f"Semantic reranking failed, falling back to structural rank: {e}")
                    ranked = ranked[:15]
            else:
                ranked = ranked[:15]

            context_files = [p for p, _ in ranked]
            code_snippets = select_snippets(file_map, ranked, max_chars=16000, lines_per_file=150)
            prompt = build_chat_prompt(structure, metadata_block, code_snippets, body.message)

            yield f"data: {json.dumps({'type': 'status', 'message': 'Consulting AI model...'})}\n\n"

            chat_deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
            response = azure_client.chat.completions.create(
                model=chat_deployment,
                messages=[
                    {"role": "system", "content": "You are a helpful and expert AI code assistant specialized in documentation. Output your responses directly in raw Markdown. NEVER wrap your entire response in a markdown code fence (```markdown ... ```). Only use code fences for actual code snippets. When generating documentation, start directly with the heading (e.g., '# Project Name')."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=4000,
                stream=True,
            )

            # IMPORTANT: Iterate the synchronous OpenAI stream in a thread pool.
            # The sync `next(iterator)` blocks until Azure sends the next token.
            # If we run it on the event loop, uvicorn can't flush previous chunks
            # to the browser — causing the entire response to appear at once.
            _sentinel = object()
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
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("api:app", host="0.0.0.0", port=port)
