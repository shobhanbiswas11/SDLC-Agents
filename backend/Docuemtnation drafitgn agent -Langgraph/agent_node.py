"""
agent_node.py — LangGraph node implementations for the Documentation Drafting Agent.

Replaces workflow.py (Temporal) + activities.py (Temporal activities).

Three nodes:
  - gather_context_node : Runs ONCE per session. Scans workspace using the RAG
                          pipeline (parsers/ + intelligence/), then injects the
                          ranked codebase context as a system message into history.
  - llm_node            : Calls Azure OpenAI → decides next action (tool or final answer)
  - tool_node           : Executes tool calls from tools.py, handles ask_user via interrupt()

Helper functions (_get_openai_client, _trim_history) ported from activities.py.
"""

from __future__ import annotations
import re
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from langgraph.types import interrupt

from config_loader import load_all_config
from tools import TOOL_HANDLERS

# ── Load config once ──────────────────────────────────────────────────────────
SYSTEM_PROMPT, TOOL_SCHEMAS, TOOL_NAMES = load_all_config()


# ── Azure OpenAI Client (cached, refreshed every 30 min) ─────────────────────

_cached_client = None
_cached_client_time = 0.0
_cached_sync_client = None
_cached_sync_client_time = 0.0
_CLIENT_TTL = 1800  # 30 minutes

# ── Cache agent.yaml settings at startup ────────────────────────────────────
try:
    import yaml as _yaml
    _cfg_path = Path(__file__).parent / "config" / "agent.yaml"
    with open(_cfg_path, encoding="utf-8") as _f:
        _agent_cfg = _yaml.safe_load(_f)
    _MAX_TOKENS = int(_agent_cfg.get("settings", {}).get("max_tokens", 16000))
except Exception:
    _MAX_TOKENS = 16000


def _get_openai_client():
    """Build or return a cached Azure OpenAI async client."""
    global _cached_client, _cached_client_time

    if _cached_client and (time.time() - _cached_client_time) < _CLIENT_TTL:
        return _cached_client

    from openai import AsyncAzureOpenAI
    from azure.identity import ClientSecretCredential

    endpoint      = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_version   = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    tenant_id     = os.getenv("AZURE_TENANT_ID", "")
    client_id     = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")

    if tenant_id and client_id and client_secret:
        cred   = ClientSecretCredential(tenant_id, client_id, client_secret)
        token  = cred.get_token("https://cognitiveservices.azure.com/.default")
        client = AsyncAzureOpenAI(
            azure_endpoint=endpoint, api_version=api_version, api_key=token.token
        )
    else:
        client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_version=api_version,
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        )

    _cached_client      = client
    _cached_client_time = time.time()
    return client


def _get_sync_openai_client():
    """Build a cached synchronous Azure OpenAI client (needed for intent check and RAG)."""
    global _cached_sync_client, _cached_sync_client_time

    if _cached_sync_client and (time.time() - _cached_sync_client_time) < _CLIENT_TTL:
        return _cached_sync_client

    from openai import AzureOpenAI
    from azure.identity import ClientSecretCredential

    endpoint      = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_version   = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    tenant_id     = os.getenv("AZURE_TENANT_ID", "")
    client_id     = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")

    if tenant_id and client_id and client_secret:
        cred   = ClientSecretCredential(tenant_id, client_id, client_secret)
        token  = cred.get_token("https://cognitiveservices.azure.com/.default")
        client = AzureOpenAI(
            azure_endpoint=endpoint, api_version=api_version, api_key=token.token
        )
    else:
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_version=api_version,
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        )

    _cached_sync_client      = client
    _cached_sync_client_time = time.time()
    return client


# ── Token counter ─────────────────────────────────────────────────────────────

def _get_token_count(messages: list[dict], model: str = "gpt-4o") -> int:
    """Return approximate token count for a list of messages."""
    try:
        import tiktoken
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = 0
        for message in messages:
            num_tokens += 3
            for key, value in message.items():
                if value:
                    num_tokens += len(encoding.encode(str(value)))
        num_tokens += 3
        return num_tokens
    except ImportError:
        total_chars = sum(len(str(v)) for m in messages for v in m.values() if v)
        return total_chars // 4


# ── History trimmer (sliding window) ─────────────────────────────────────────

def _trim_history(messages: list[dict], max_tokens: int = 120_000) -> list[dict]:
    """
    Keep the system message(s) + as many recent messages as fit within max_tokens.
    Drops oldest messages first, guarding against orphaned tool messages.
    Mirrors the sliding window logic in the original workflow.py.
    """
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system  = [m for m in messages if m.get("role") != "system"]

    MAX_RECENT = 20
    if len(non_system) > MAX_RECENT:
        slice_idx = len(non_system) - MAX_RECENT
        # Avoid cutting inside a tool-call sequence — scan forward to next user message
        while slice_idx < len(non_system) and non_system[slice_idx].get("role") != "user":
            slice_idx += 1
        if slice_idx == len(non_system):
            slice_idx = len(non_system) - MAX_RECENT  # fallback
        non_system = non_system[slice_idx:]

    while len(non_system) > 1:
        if _get_token_count(system_msgs + non_system) <= max_tokens:
            break
        removed = non_system.pop(0)
        if removed.get("role") == "assistant" and removed.get("tool_calls"):
            while non_system and non_system[0].get("role") == "tool":
                non_system.pop(0)
        while non_system and non_system[0].get("role") == "tool":
            non_system.pop(0)

    return system_msgs + non_system


# ── Gather Context Node (RAG Pre-processing) ──────────────────────────────────

# Keywords that trigger a fresh RAG re-index even mid-session
_REINDEX_PATTERNS = re.compile(
    r"\b(rescan|re-scan|re-?index|reindex|re-?analyz|reanalyz|look at .+ folder|switch to .+ folder|analyze .+ instead)",
    re.IGNORECASE,
)


def _smart_snippet(content: str, max_chars: int = 4000) -> str:
    """Return a smarter snippet: first 60% + last 20% of allowed chars."""
    if len(content) <= max_chars:
        return content
    head_len = int(max_chars * 0.65)
    tail_len = max_chars - head_len
    return content[:head_len] + "\n...\n" + content[-tail_len:]


async def gather_context_node(state: dict) -> dict:
    """
    Run the full RAG pipeline at the start of a session (or on re-index trigger).

    Sets context_gathered=True so this node is skipped on follow-up turns
    UNLESS the user's message contains re-index keywords.
    """
    workspace_path = state.get("workspace_path", ".")
    history        = list(state.get("history", []))

    # Extract the LAST user message (may differ from first on re-index turns)
    query = ""
    for msg in reversed(history):
        if msg.get("role") == "user":
            query = msg.get("content", "")
            break

    context_str = f"Codebase Context ({workspace_path}):\n"

    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))

        from parsers.tree_fetcher     import fetch_local_repo
        from parsers.metadata_extractor import extract_all_metadata, format_metadata_block
        from parsers.ast_graph_builder  import build_combined_graph
        from intelligence.file_ranker   import rank_files
        from intelligence.semantic_ranker import semantic_rerank

        if not os.path.exists(workspace_path):
            context_str += f"Warning: workspace '{workspace_path}' does not exist.\n"
        else:
            # ── Quick intent check using google.genai SDK ──────────────────
            try:
                from google import genai as _sdk
                _genai_key = os.getenv("GEMINI_API_KEY", "")
                if _genai_key:
                    _gclient = _sdk.Client(api_key=_genai_key)
                    _intent_model = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
                    _intent_prompt = (
                        "You are an intent analyzer. Output EXACTLY one word/token:\n"
                        "- 'SKIP_RAG' if this is a greeting, small-talk, or a generic question that clearly does NOT require scanning source code.\n"
                        "- A folder name if the user specifically asks to analyze that folder/directory.\n"
                        "- '.' if the user needs code analysis but doesn't specify a folder.\n"
                        "Output NOTHING else."
                    )
                    _resp = _gclient.models.generate_content(
                        model=_intent_model,
                        contents=query,
                        config={"system_instruction": _intent_prompt, "temperature": 0, "max_output_tokens": 10},
                    )
                    target_dir = _resp.text.strip().strip("'\"")
                else:
                    # Fallback to Azure if no Gemini key
                    sync_client = _get_sync_openai_client()
                    chat_dep    = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
                    sys_msg     = ("Output EXACTLY one word: 'SKIP_RAG' if general question, "
                                   "a folder name if specific folder, '.' otherwise.")
                    _r = sync_client.chat.completions.create(
                        model=chat_dep,
                        messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": query}],
                        temperature=0, max_tokens=20,
                    )
                    target_dir = _r.choices[0].message.content.strip().strip("'\"")
            except Exception as e:
                print(f"[gather_context] Intent check failed: {e}")
                target_dir = "."

            if target_dir == "SKIP_RAG":
                print("[gather_context] General question detected. Skipping RAG pipeline.")
                return {**state, "history": history, "context_gathered": True, "status": "thinking"}

            if target_dir not in (".", ""):
                potential = os.path.join(workspace_path, target_dir)
                if os.path.isdir(potential):
                    workspace_path = potential
                    print(f"[gather_context] Scoped scan to: {target_dir}")

            # ── Run the RAG pipeline in a thread (CPU-bound) ──────────────
            file_map, file_tree = await asyncio.to_thread(fetch_local_repo, workspace_path)

            if not file_tree:
                context_str += "No files found in workspace.\n"
            else:
                # Metadata
                try:
                    cached_metadata = await asyncio.to_thread(extract_all_metadata, file_map)
                    metadata_block  = format_metadata_block(cached_metadata)
                except Exception as e:
                    print(f"[gather_context] Metadata extraction failed: {e}")
                    metadata_block = "Metadata unavailable."

                # Graph + ranking
                try:
                    graph   = await asyncio.to_thread(build_combined_graph, file_map)
                    ranked  = await asyncio.to_thread(rank_files, file_map, file_tree, graph, 20, False)
                except Exception as e:
                    print(f"[gather_context] Basic ranking failed: {e}")
                    ranked = [(p, 1.0) for p in list(file_map.keys())[:20]]

                # Semantic reranking
                try:
                    if query:
                        emb_dep       = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-2")
                        ranked        = semantic_rerank(
                            ranked[:30], file_map, model=emb_dep,
                            query=query, top_k=15, cached_embeddings={},
                        )
                    else:
                        ranked = ranked[:15]
                except Exception as e:
                    print(f"[gather_context] Semantic reranking failed: {e}")
                    ranked = ranked[:15]

                # Build context string
                context_str += f"Tree (first 100 items):\n{chr(10).join(file_tree[:100])}\n\n"
                context_str += f"Metadata:\n{metadata_block}\n\n"
                context_str += "Top Relevant Files:\n"
                for p, _ in ranked:
                    if p in file_map:
                        context_str += f"\n--- {p} ---\n{_smart_snippet(file_map[p])}\n"

    except ImportError as e:
        context_str += f"Warning: Could not load RAG modules ({e}). Running without pre-gathered context.\n"
    except Exception as e:
        context_str += f"Warning: RAG pipeline failed ({e}). Continuing without context.\n"

    # Inject context as a second system message right after the agent's system prompt
    # (position 1 — after the original system prompt at position 0)
    system_injection = {"role": "system", "content": f"PRE-GATHERED RAG CONTEXT:\n{context_str}"}
    updated_history  = []
    injected         = False
    for msg in history:
        updated_history.append(msg)
        if msg.get("role") == "system" and not injected:
            updated_history.append(system_injection)
            injected = True
    if not injected:
        updated_history.insert(0, system_injection)

    return {
        **state,
        "history":          updated_history,
        "context_gathered": True,
        "status":           "thinking",
    }


# ── LLM Node ──────────────────────────────────────────────────────────────────

async def llm_node(state: dict) -> dict:
    """
    Call Azure OpenAI with the current conversation history and tool schemas.

    Returns updated state with either:
      - pending_tool_calls populated (agent wants to use a tool), or
      - last_response set to the final text answer (agent is done)
    """
    client     = _get_openai_client()
    deployment = (
        os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    )

    max_tokens = _MAX_TOKENS

    history = state.get("history", [])
    trimmed = _trim_history(history)

    try:
        response = await client.chat.completions.create(
            model=deployment,
            messages=trimmed,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.3,
            max_completion_tokens=max_tokens,
            timeout=120,
        )
    except Exception as exc:
        error_msg = f"⚠️ LLM call failed: {type(exc).__name__}: {str(exc)[:200]}"
        return {
            **state,
            "last_response":     error_msg,
            "pending_tool_calls": [],
            "status":            "idle",
            "history":           history + [{"role": "assistant", "content": error_msg}],
        }

    message = response.choices[0].message

    # ── Agent wants to call tools ──
    if message.tool_calls:
        tool_calls_data = [
            {
                "id":        tc.id,
                "name":      tc.function.name,
                "arguments": tc.function.arguments,
            }
            for tc in message.tool_calls
        ]
        print("[llm_node] Tool calls:", [tc["name"] for tc in tool_calls_data])

        updated_history = history + [
            {
                "role":       "assistant",
                "content":    None,
                "tool_calls": [
                    {
                        "id":   tc["id"],
                        "type": "function",
                        "function": {
                            "name":      tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }
                    for tc in tool_calls_data
                ],
            }
        ]

        return {
            **state,
            "pending_tool_calls": tool_calls_data,
            "history":            updated_history,
            "status":             "thinking",
        }

    # ── Agent gave a final text answer ──
    text = message.content or ""
    return {
        **state,
        "pending_tool_calls": [],
        "last_response":      text,
        "status":             "idle",
        "history":            history + [{"role": "assistant", "content": text}],
    }


# ── Tool Node ─────────────────────────────────────────────────────────────────

async def tool_node(state: dict) -> dict:
    """
    Execute the tool calls requested by the LLM.

    Special handling:
      - ask_user → calls LangGraph interrupt(), which pauses the graph and
                   waits for the human to supply an answer via /sessions/{id}/answer.
                   The graph automatically resumes when Command(resume=answer) is sent.

    All other tools are looked up in tools.TOOL_HANDLERS and executed directly.
    """
    tool_calls     = state.get("pending_tool_calls", [])
    history        = list(state.get("history", []))
    workspace_path = state.get("workspace_path", ".")
    navigated_file = state.get("navigated_file", "")
    created_files  = list(state.get("created_files", []))

    for tool_call in tool_calls:
        tool_name = tool_call["name"]

        # Parse arguments
        try:
            tool_args = json.loads(tool_call["arguments"])
        except json.JSONDecodeError as exc:
            history.append({
                "role":         "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps({
                    "status": "error",
                    "error": (
                        f"Your tool arguments were invalid JSON: {exc}. "
                        f"Raw: {tool_call['arguments'][:200]}... "
                        "Please retry with shorter, valid JSON arguments."
                    ),
                }),
            })
            continue

        # ── ask_user → pause graph, wait for human ──
        if tool_name == "ask_user":
            question    = tool_args.get("question", "")
            answer      = interrupt(question)   # LangGraph pauses here ✋
            tool_result = {"status": "success", "answer": answer}

        # ── all other tools ──
        else:
            handler = TOOL_HANDLERS.get(tool_name)
            if handler is None:
                tool_result = {
                    "status": "error",
                    "error": (
                        f"Unknown tool: '{tool_name}'. "
                        f"Available: {list(TOOL_HANDLERS.keys())}"
                    ),
                }
            else:
                try:
                    # Auto-inject workspace_path, github_token, and repo url if not already in args
                    if "workspace_path" not in tool_args:
                        tool_args["workspace_path"] = workspace_path
                    if "github_token" not in tool_args and state.get("github_token"):
                        tool_args["github_token"] = state["github_token"]
                    if "github_repo" not in tool_args and state.get("repo_url"):
                        tool_args["github_repo"] = state["repo_url"]
                    tool_result = await handler(**tool_args)
                except Exception as exc:
                    tool_result = {
                        "status": "error",
                        "error":  f"Tool '{tool_name}' raised: {str(exc)}",
                    }

        # ── Track file events for the frontend ──
        if tool_name == "write_file" and tool_result.get("status") == "success":
            fp = tool_result.get("file_path") or tool_args.get("file_path", "")
            if fp:
                navigated_file = fp
                if fp not in created_files:
                    created_files.append(fp)

        elif tool_name == "read_file" and tool_result.get("status") == "success":
            fp = tool_args.get("file_path", "")
            if fp:
                navigated_file = fp

        # Append tool result to history
        history.append({
            "role":         "tool",
            "tool_call_id": tool_call["id"],
            "content":      json.dumps(tool_result),
        })

    return {
        **state,
        "pending_tool_calls": [],
        "history":            history,
        "navigated_file":     navigated_file,
        "created_files":      created_files,
        "status":             "thinking",
    }
