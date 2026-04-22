"""
agent_node.py — LangGraph node implementations for the Code Refactoring Agent.

Replaces activities.py (Temporal).

Two nodes replace the old Temporal activities:
  - llm_node  : calls Azure OpenAI → decides next action (tool or final answer)
  - tool_node : executes tool calls from tools.py, handles ask_user via interrupt()

Helper functions (_get_openai_client, _trim_history, _get_token_count,
_augment_message_with_github_paths) are ported unchanged from the original
activities.py and workflow.py.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any
from urllib.parse import unquote

from langgraph.types import interrupt

from config_loader import load_all_config
from tools import TOOL_HANDLERS

# ── Load config once ──────────────────────────────────────────────────────────
SYSTEM_PROMPT, TOOL_SCHEMAS, TOOL_NAMES = load_all_config()


# ── Azure OpenAI Client (cached, refreshed every 30 min) ─────────────────────

_cached_client = None
_cached_client_time = 0.0
_CLIENT_TTL = 1800  # 30 minutes


def _get_openai_client():
    """Build or return a cached Azure OpenAI async client."""
    global _cached_client, _cached_client_time

    if _cached_client and (time.time() - _cached_client_time) < _CLIENT_TTL:
        return _cached_client

    from openai import AsyncAzureOpenAI
    from azure.identity import ClientSecretCredential

    endpoint       = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_version    = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    tenant_id      = os.getenv("AZURE_TENANT_ID", "")
    client_id      = os.getenv("AZURE_CLIENT_ID", "")
    client_secret  = os.getenv("AZURE_CLIENT_SECRET", "")

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


# ── Token counter (ported from activities.py) ─────────────────────────────────

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


# ── History trimmer (ported from activities.py) ───────────────────────────────

def _trim_history(messages: list[dict], max_tokens: int = 120_000) -> list[dict]:
    """
    Keep the system message + as many recent messages as fit within max_tokens.
    Drops oldest messages first while guarding against orphaned tool messages.
    """
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system  = [m for m in messages if m.get("role") != "system"]

    while len(non_system) > 1:
        if _get_token_count(system_msgs + non_system) <= max_tokens:
            break

        removed = non_system.pop(0)

        # Guard: never leave a 'tool' result without its 'assistant' call
        if removed.get("role") == "assistant" and removed.get("tool_calls"):
            while non_system and non_system[0].get("role") == "tool":
                non_system.pop(0)

        # Guard: drop any orphaned leading tool messages
        while non_system and non_system[0].get("role") == "tool":
            non_system.pop(0)

    return system_msgs + non_system


# ── GitHub URL augmentation (ported from workflow.py) ─────────────────────────

def _augment_message_with_github_paths(message: str, workspace_path: str = ".") -> str:
    """
    If user provides a GitHub blob URL, append a normalized repository-relative
    file path hint so the agent can call file tools correctly.
    """
    pattern = re.compile(
        r"https?://github\.com/[^/\s]+/[^/\s]+/blob/[^/\s]+/(?P<path>[^\s?#]+)"
    )
    matches = list(pattern.finditer(message))
    if not matches:
        return message

    extracted_paths: list[str] = []
    for match in matches:
        path = unquote(match.group("path")).strip().lstrip("/")
        if path and path not in extracted_paths:
            extracted_paths.append(path)

    if not extracted_paths:
        return message

    is_github_backed = ".refactor_repos" in (workspace_path or "")
    hint_lines = ["", "Detected GitHub blob URL(s)."]

    if is_github_backed:
        hint_lines.append(
            "This session is GitHub-backed. Prefer these repository-relative file path(s):"
        )
        hint_lines.extend([f"- {path}" for path in extracted_paths])
    else:
        hint_lines.append(
            "This session is local (not a cloned GitHub workspace). "
            "Use the full GitHub URL directly with read_file/analyze_code. "
            "Do NOT use repository-relative paths in this session."
        )

    return message + "\n" + "\n".join(hint_lines)


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

    history = state.get("history", [])
    trimmed = _trim_history(history)

    try:
        response = await client.chat.completions.create(
            model=deployment,
            messages=trimmed,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.2,
            max_completion_tokens=4096,
            timeout=60,
        )
    except Exception as exc:
        error_msg = f"⚠️ LLM call failed: {type(exc).__name__}: {str(exc)[:200]}"
        return {
            **state,
            "last_response":    error_msg,
            "pending_tool_calls": [],
            "status":           "idle",
            "history":          history + [{"role": "assistant", "content": error_msg}],
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
      - ask_user  → calls LangGraph interrupt(), which pauses the graph and
                    waits for the human to supply an answer via /answer endpoint.
                    The graph automatically resumes when Command(resume=answer) is sent.

    All other tools are looked up in tools.TOOL_HANDLERS and executed directly.
    Navigation events (navigate_to_file, read_file, write_file) update
    navigated_file / created_files in state for the frontend.
    """
    tool_calls     = state.get("pending_tool_calls", [])
    history        = list(state.get("history", []))
    workspace_path = state.get("workspace_path", ".")
    navigated_file = state.get("navigated_file", "")
    created_files  = list(state.get("created_files", []))

    for tool_call in tool_calls:
        tool_name = tool_call["name"]

        # Parse arguments — LLM sometimes returns truncated / invalid JSON
        try:
            tool_args = json.loads(tool_call["arguments"])
        except json.JSONDecodeError as exc:
            history.append({
                "role":        "tool",
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
                    tool_result = await handler(workspace_path=workspace_path, **tool_args)
                except Exception as exc:
                    tool_result = {
                        "status": "error",
                        "error":  f"Tool '{tool_name}' raised: {str(exc)}",
                    }

        # ── Track navigation / file-creation events ──
        if tool_name == "navigate_to_file" and tool_result.get("status") == "success":
            nav = tool_result.get("resolved_path") or tool_args.get("file_path", "")
            if nav:
                navigated_file = nav

        elif tool_name == "read_file" and tool_result.get("status") == "success":
            rp = tool_result.get("resolved_path") or tool_args.get("file_path", "")
            if rp:
                navigated_file = rp

        elif tool_name == "write_file" and tool_result.get("status") == "success":
            if tool_result.get("created"):
                fp = tool_result.get("file_path") or tool_args.get("file_path", "")
                if fp and fp not in created_files:
                    created_files.append(fp)
            nav = tool_result.get("file_path") or tool_args.get("file_path", "")
            if nav:
                navigated_file = nav

        # Append tool result to history
        history.append({
            "role":        "tool",
            "tool_call_id": tool_call["id"],
            "content":     json.dumps(tool_result),
        })

    return {
        **state,
        "pending_tool_calls": [],
        "history":            history,
        "navigated_file":     navigated_file,
        "created_files":      created_files,
        "status":             "thinking",
    }
