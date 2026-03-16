# main.py
import os
import base64
import hashlib
import hmac
import requests
import re
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

# Import the process function from your pipeline
from process_automated_readme import process_automated_readme, push_readme_to_target
from memory.preferences import load_preferences, save_preferences
from parsers.tree_fetcher import fetch_full_repo, fetch_local_repo
from parsers.ast_graph_builder import build_combined_graph
from generators.diagram_generator import build_diagram_summary
from generators.section_detector import detect_existing_sections, fetch_existing_readme_github, fetch_existing_readme_local
from intelligence.file_ranker import rank_files
from intelligence.semantic_ranker import semantic_rerank
from intelligence.context_selector import select_snippets
from parsers.metadata_extractor import format_metadata_block, extract_all_metadata
from core.cache_manager import load_cache
from intelligence.chat_prompt import build_chat_prompt
from process_automated_readme import (
    get_azure_client, AZURE_OPENAI_CHATGPT_DEPLOYMENT, 
    USE_SEMANTIC_RANKING, AZURE_OPENAI_EMBEDDING_DEPLOYMENT, 
    _HAS_GITHUB_LOADER, load_github_repo
)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DocuGenius API")

_cors_origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://localhost:13100")
_cors_origins = [origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _normalize_repo_identifier(repo_value: str) -> str:
    """
    Accept either:
      - owner/repo
      - https://github.com/owner/repo
      - github.com/owner/repo
    and normalize to owner/repo.
    """
    raw = (repo_value or "").strip()
    if not raw:
        raise ValueError("repo cannot be empty")

    patterns = [
        r"^https?://(?:www\.)?github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)",
        r"^(?:www\.)?github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)",
    ]
    for pattern in patterns:
        match = re.match(pattern, raw)
        if match:
            owner = match.group("owner").strip()
            repo = match.group("repo").strip()
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


class PushReadmeRequest(BaseModel):
    repo: str
    access_token: str
    branch: str = "main"
    commit_message: str = "Update README via DocuGenius"
    local_path: Optional[str] = None
    custom_instructions: Optional[str] = None
    sections: Optional[list[str]] = None
    target_audience: Optional[str] = "Mixed"
    auto_commit: bool = True

class CommitReadmeRequest(BaseModel):
    repo: str
    access_token: str
    local_path: Optional[str] = None
    markdown_content: str

class ChatRequest(BaseModel):
    repo: str
    access_token: str
    local_path: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    answer: str
    context_files: list[str]


@app.post("/push-readme")
async def push_readme(body: PushReadmeRequest):
    """
    Dynamically generates and pushes a README file.
    (Non-streaming version)
    """
    if body.local_path:
        owner, repo_name = "", ""
        token = ""
        normalized_repo = ""
    else:
        token = body.access_token or os.environ.get("YOUR_GITHUB_ACCESS_TOKEN", "")
        if not token:
            raise HTTPException(status_code=400, detail="GitHub access token required for remote repositories")

        try:
            normalized_repo = _normalize_repo_identifier(body.repo)
            owner, repo_name = normalized_repo.split("/", 1)
        except ValueError:
            raise HTTPException(status_code=400, detail="repo should be in the format 'owner/repo' or a GitHub URL")

    try:
        # Generate and push README dynamically
        await process_automated_readme(
            repo_name=normalized_repo if not body.local_path else "",
            token=token,
            local_path=body.local_path,
            include_all_files=False,
            custom_instructions=body.custom_instructions,
            sections=body.sections,
            target_audience=body.target_audience,
        )
        return {
            "status": "success",
            "message": f"README generated and pushed for {normalized_repo or body.repo}",
            "file_url": f"https://github.com/{owner}/{repo_name}/blob/{body.branch}/README.md",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating README: {str(e)}")

@app.post("/commit-readme")
async def commit_readme(body: CommitReadmeRequest):
    """
    Manually commits or saves a generated README if auto_commit was disabled.
    """
    if body.local_path:
        owner, repo_name = "", ""
        token = ""
        normalized_repo = ""
    else:
        token = body.access_token or os.environ.get("YOUR_GITHUB_ACCESS_TOKEN", "")
        if not token:
            raise HTTPException(status_code=400, detail="GitHub access token required for remote repositories")

        try:
            normalized_repo = _normalize_repo_identifier(body.repo)
            owner, repo_name = normalized_repo.split("/", 1)
        except ValueError:
            raise HTTPException(status_code=400, detail="repo should be in the format 'owner/repo' or a GitHub URL")

    try:
        await push_readme_to_target(
            md_content=body.markdown_content,
            repo_name=normalized_repo if not body.local_path else "",
            token=token,
            local_path=body.local_path,
        )
        return {
            "status": "success",
            "message": "README committed successfully."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error committing README: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest):
    """
    Codebase Chatbot: Answers user questions based on the repo's structure, 
    metadata, and semantically relevant source code.
    """
    if body.local_path:
        owner, repo_name = "", ""
        token = ""
        normalized_repo = ""
    else:
        token = body.access_token or os.environ.get("YOUR_GITHUB_ACCESS_TOKEN", "")
        if not token:
            raise HTTPException(status_code=400, detail="GitHub access token required for remote repositories")

        try:
            normalized_repo = _normalize_repo_identifier(body.repo)
            owner, repo_name = normalized_repo.split("/", 1)
        except ValueError:
            raise HTTPException(status_code=400, detail="repo should be in the format 'owner/repo' or a GitHub URL")

    target_name = body.local_path if body.local_path else normalized_repo

    try:
        # 1. Fetch Repo
        if body.local_path:
            file_map, file_tree = fetch_local_repo(body.local_path)
        else:
            file_map, file_tree = fetch_full_repo(
                normalized_repo, token, branch="main",
                loader_fn=load_github_repo if _HAS_GITHUB_LOADER else None,
                prefer_loader=_HAS_GITHUB_LOADER,
            )

        if not file_tree:
            raise HTTPException(status_code=404, detail="No documents found to parse.")

        # 2. Get Metadata Cache
        cache_key = target_name.replace("/", "_").replace("\\", "_")
        cache = load_cache(cache_key)
        cached_metadata = cache.get("file_metadata", {})
        if not cached_metadata:
            # Fallback if cache is entirely empty (rare case if chatting before README generation)
            cached_metadata = extract_all_metadata(file_map)

        metadata_block = format_metadata_block(cached_metadata)
        structure = "\n".join([f"Repository: {target_name}"] + file_tree)

        # 3. Build basic graph and heuristic ranking
        graph = build_combined_graph(file_map)
        ranked = rank_files(file_map, file_tree, graph, top_k=40, include_all=False)

        # 4. Semantic Re-ranking using the user's message as query
        azure_client = get_azure_client()
        if USE_SEMANTIC_RANKING:
            file_embeddings = cache.setdefault("file_embeddings", {})
            initial_emb_count = len(file_embeddings)
            
            ranked = semantic_rerank(
                ranked[:40], 
                file_map, 
                azure_client, 
                AZURE_OPENAI_EMBEDDING_DEPLOYMENT, 
                query=body.message,
                top_k=5,
                cached_embeddings=file_embeddings
            )
            
            if len(file_embeddings) > initial_emb_count:
                from core.cache_manager import save_cache
                save_cache(cache_key, cache.get("file_metadata", {}), cache.get("import_graph", {}), file_embeddings)
        else:
            ranked = ranked[:5] # Just take top 5 heuristic if semantic is turned off

        context_files = [p for p, s in ranked]

        # 5. Extract snippets for top matching files (give it a good chunk)
        code_snippets = select_snippets(file_map, ranked, max_chars=16000, lines_per_file=150)

        # 6. Build Chat Prompt
        prompt = build_chat_prompt(structure, metadata_block, code_snippets, body.message)

        # 7. Call Azure OpenAI (Chat Completions)
        print(f"Calling Azure OpenAI for Chat endpoint, requesting answer for: {body.message[:50]}...")
        response = azure_client.chat.completions.create(
            model=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a helpful and expert AI code assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3, # Lower temp for more factual codebase answers
            max_tokens=2000
        )

        answer_md = response.choices[0].message.content.strip()

        return ChatResponse(
            answer=answer_md,
            context_files=context_files
        )

    except Exception as e:
        print(f"Error in /chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream-chat")
async def stream_chat_endpoint(body: ChatRequest):
    """
    Codebase Chatbot via Server-Sent Events (SSE).
    Streams chunks of the AI's response to the client immediately
    to eliminate long loading screens and perceived latency.
    """
    if body.local_path:
        owner, repo_name = "", ""
        token = ""
        normalized_repo = ""
    else:
        token = body.access_token or os.environ.get("YOUR_GITHUB_ACCESS_TOKEN", "")
        if not token:
            raise HTTPException(status_code=400, detail="GitHub access token required for remote repositories")

        try:
            normalized_repo = _normalize_repo_identifier(body.repo)
            owner, repo_name = normalized_repo.split("/", 1)
        except ValueError:
            raise HTTPException(status_code=400, detail="repo should be in the format 'owner/repo' or a GitHub URL")

    target_name = body.local_path if body.local_path else normalized_repo

    async def event_generator():
        try:
            # Yield initial connecting event
            yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching code context...'})}\n\n"

            # 1. Fetch Repo
            if body.local_path:
                file_map, file_tree = fetch_local_repo(body.local_path)
            else:
                file_map, file_tree = fetch_full_repo(
                    normalized_repo, token, branch="main",
                    loader_fn=load_github_repo if _HAS_GITHUB_LOADER else None,
                    prefer_loader=_HAS_GITHUB_LOADER,
                )

            if not file_tree:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No documents found to parse.'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing codebase and ranking files...'})}\n\n"

            # 2. Get Metadata Cache
            cache_key = target_name.replace("/", "_").replace("\\", "_")
            cache = load_cache(cache_key)
            cached_metadata = cache.get("file_metadata", {})
            if not cached_metadata:
                cached_metadata = extract_all_metadata(file_map)

            metadata_block = format_metadata_block(cached_metadata)
            structure = "\n".join([f"Repository: {target_name}"] + file_tree)

            # 3. Build basic graph and heuristic ranking
            graph = build_combined_graph(file_map)
            ranked = rank_files(file_map, file_tree, graph, top_k=40, include_all=False)

            # 4. Semantic Re-ranking using the user's message as query
            azure_client = get_azure_client()
            if USE_SEMANTIC_RANKING:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Performing semantic intelligence ranking...'})}\n\n"
                file_embeddings = cache.setdefault("file_embeddings", {})
                initial_emb_count = len(file_embeddings)
                
                ranked = semantic_rerank(
                    ranked[:40], 
                    file_map, 
                    azure_client, 
                    AZURE_OPENAI_EMBEDDING_DEPLOYMENT, 
                    query=body.message,
                    top_k=5,
                    cached_embeddings=file_embeddings
                )
                
                if len(file_embeddings) > initial_emb_count:
                    from core.cache_manager import save_cache
                    save_cache(cache_key, cache.get("file_metadata", {}), cache.get("import_graph", {}), file_embeddings)
            else:
                ranked = ranked[:5]

            context_files = [p for p, s in ranked]

            # 5. Extract snippets
            code_snippets = select_snippets(file_map, ranked, max_chars=16000, lines_per_file=150)

            # 6. Build Chat Prompt
            prompt = build_chat_prompt(structure, metadata_block, code_snippets, body.message)

            yield f"data: {json.dumps({'type': 'status', 'message': 'Consulting AI model...'})}\n\n"

            # 7. Call Azure OpenAI with STREAMING ENABLED
            response = azure_client.chat.completions.create(
                model=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "You are a helpful and expert AI code assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3, 
                max_tokens=2000,
                stream=True  # MAGIC BULLET FOR FAST RESPONSES
            )

            for chunk in response:
                if len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        # Yield the actual text chunks from the AI
                        yield f"data: {json.dumps({'type': 'content', 'chunk': delta.content})}\n\n"

            # Finally, yield the context files so the frontend knows what was read
            yield f"data: {json.dumps({'type': 'done', 'context_files': context_files})}\n\n"

        except Exception as e:
            print(f"Error in /stream-chat endpoint: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")




@app.post("/stream-readme")
async def stream_readme(body: PushReadmeRequest):
    """
    Dynamically generates a README file for a GitHub repo or local directory.
    Streams progress iteratively to the client via Server-Sent Events (SSE).
    """
    if body.local_path:
        owner, repo_name = "", ""
        token = ""
        normalized_repo = ""
    else:
        token = body.access_token or os.environ.get("YOUR_GITHUB_ACCESS_TOKEN", "")
        if not token:
            raise HTTPException(status_code=400, detail="GitHub access token required for remote repositories")

        try:
            normalized_repo = _normalize_repo_identifier(body.repo)
            owner, repo_name = normalized_repo.split("/", 1)
        except ValueError:
            raise HTTPException(status_code=400, detail="repo should be in the format 'owner/repo' or a GitHub URL")

    async def event_generator():
        queue = asyncio.Queue()

        async def callback(msg_dict):
            await queue.put(msg_dict)
            
        def task_done_callback(future):
            # Once the background processing is completely finished, signal the queue.
            try:
                future.result()
            except Exception as e:
                # If there's an uncaught exception, send it to the UI
                queue.put_nowait({"step": "error", "status": "error", "message": str(e)})
            queue.put_nowait(None)

        task = asyncio.create_task(
            process_automated_readme(
                repo_name=normalized_repo if not body.local_path else "",
                token=token,
                local_path=body.local_path,
                include_all_files=False,
                custom_instructions=body.custom_instructions,
                sections=body.sections,
                target_audience=body.target_audience,
                auto_commit=body.auto_commit,
                progress_callback=callback
            )
        )
        task.add_done_callback(task_done_callback)

        while True:
            msg = await queue.get()
            if msg is None:
                break
            
            # Format as Server-Sent Event
            # Looks like: data: {"step": "fetching", "status": "running", "message": "..."}
            yield f"data: {json.dumps(msg)}\n\n"
            
            if msg.get("step") == "done" or msg.get("step") == "error":
                # We can stop streaming
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    GitHub webhook endpoint. When a push to main occurs, this triggers
    process_automated_readme in the background (returns quickly to GitHub).
    Validates the X-Hub-Signature-256 header if GITHUB_WEBHOOK_SECRET is set.
    """
    raw_body = await request.body()

    # --- Signature Validation ---
    if GITHUB_WEBHOOK_SECRET:
        sig_header = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(
            GITHUB_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        import json as _json
        payload = _json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Avoid re-triggering from our own commit message
    commits = payload.get("commits", [])
    if commits and any("Update README via DocuGenius" in c.get("message", "") for c in commits):
        return {"status": "ignored", "reason": "Self-triggered commit"}

    repo_name = payload.get("repository", {}).get("full_name")
    branch_ref = payload.get("ref", "")

    # Only trigger for pushes to the main branch
    if not repo_name or "refs/heads/main" not in branch_ref:
        return {"status": "ignored", "reason": "Not the main branch or missing repository name"}

    token = os.environ.get("YOUR_GITHUB_ACCESS_TOKEN")
    if not token:
        return {"status": "error", "reason": "Missing token in environment"}

    # --- Extract changed files from push payload ---
    changed_files = set()
    for commit in commits:
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))
        changed_files.update(commit.get("removed", []))

    print(f"[webhook] {len(changed_files)} files changed: {changed_files}")

    # --- Add Preference Check ---
    prefs = load_preferences(repo_name)
    if not prefs.get("auto_generate_on_push", True):
        print(f"[webhook] Skipped: auto_generate_on_push is disabled for {repo_name}")
        return {"status": "ignored", "reason": "auto_generate_on_push is disabled by user preferences"}

    # Kick off background task with changed_files for diff-aware processing
    background_tasks.add_task(
        process_automated_readme,
        repo_name=repo_name,
        token=token,
        include_all_files=False,
        changed_files=changed_files if changed_files else None,
    )

    return {
        "status": "success",
        "message": "Webhook received! Generating docs in background.",
        "changed_files": len(changed_files),
    }


# ── User Preferences Endpoints ────────────────────────────────────────────────

class PreferencesRequest(BaseModel):
    include_sections: list = []
    exclude_sections: list = []
    tone: str = "professional"
    extra_instructions: str = ""
    custom_badges: list = []
    auto_generate_on_push: bool = True


@app.post("/preferences/{owner}/{repo}")
async def set_preferences(owner: str, repo: str, body: PreferencesRequest):
    """Save per-repo preferences for README generation."""
    repo_name = f"{owner}/{repo}"
    path = save_preferences(repo_name, body.model_dump())
    return {
        "status": "success",
        "message": f"Preferences saved for {repo_name}",
        "file": path,
        "preferences": load_preferences(repo_name),
    }


@app.get("/preferences/{owner}/{repo}")
async def get_preferences(owner: str, repo: str):
    """Get current preferences for a repo."""
    repo_name = f"{owner}/{repo}"
    prefs = load_preferences(repo_name)
    return {"repo": repo_name, "preferences": prefs}


# ── Diagram Endpoint ──────────────────────────────────────────────────────────

class DiagramRequest(BaseModel):
    access_token: str
    branch: str = "main"


@app.post("/diagram/{owner}/{repo}")
async def get_diagram(owner: str, repo: str, body: DiagramRequest):
    """
    Fetch the architecture diagram (Mermaid) for a GitHub repository.
    Builds the import graph live and returns the Mermaid string as JSON.
    """
    repo_name = f"{owner}/{repo}"
    token = body.access_token or os.environ.get("YOUR_GITHUB_ACCESS_TOKEN", "")
    if not token:
        raise HTTPException(status_code=400, detail="GitHub access token required")
    try:
        file_map, file_tree = fetch_full_repo(repo_name, token, branch=body.branch)
        graph = build_combined_graph(file_map)
        summary = build_diagram_summary(graph)
        return {
            "status": "success",
            "repo": repo_name,
            "diagram": summary["mermaid"],
            "node_count": summary["node_count"],
            "edge_count": summary["edge_count"],
            "top_nodes": summary["top_nodes"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building diagram: {str(e)}")


@app.post("/diagram/local")
async def get_diagram_local(local_path: str):
    """
    Fetch the architecture diagram for a local repository path.
    """
    try:
        file_map, file_tree = fetch_local_repo(local_path)
        graph = build_combined_graph(file_map)
        summary = build_diagram_summary(graph)
        return {
            "status": "success",
            "local_path": local_path,
            "diagram": summary["mermaid"],
            "node_count": summary["node_count"],
            "edge_count": summary["edge_count"],
            "top_nodes": summary["top_nodes"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building diagram: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)