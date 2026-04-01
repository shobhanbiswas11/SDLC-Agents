"""
activities.py — Temporal Activities for the Code Refactoring Agent.

Two activities:
  1. llm_call  — Send messages to Azure OpenAI and get tool calls or text back.
  2. run_tool  — Find the right tool handler and execute it.
"""

import json
import os
import time
from typing import Any

from temporalio import activity

from tools import TOOL_HANDLERS


# ──────────────────────────────────────────────
# AZURE OPENAI CLIENT  (cached — created once)
# ──────────────────────────────────────────────

_cached_client = None
_cached_client_time = 0.0
_CLIENT_TTL = 1800  # refresh token every 30 min


def _get_openai_client():
    """Build or return a cached Azure OpenAI client."""
    global _cached_client, _cached_client_time

    # Return cached client if still fresh
    if _cached_client and (time.time() - _cached_client_time) < _CLIENT_TTL:
        return _cached_client

    from openai import AzureOpenAI
    from azure.identity import ClientSecretCredential

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    tenant_id = os.getenv("AZURE_TENANT_ID", "")
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")

    if tenant_id and client_id and client_secret:
        cred = ClientSecretCredential(tenant_id, client_id, client_secret)
        token = cred.get_token("https://cognitiveservices.azure.com/.default")
        client = AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=token.token)
    else:
        client = AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=os.getenv("AZURE_OPENAI_API_KEY", ""))

    _cached_client = client
    _cached_client_time = time.time()
    return client


# ──────────────────────────────────────────────
# ACTIVITY 1: LLM CALL
# ──────────────────────────────────────────────

@activity.defn(name="llm_call")
async def llm_call(messages: list[dict], tool_schemas: list[dict]) -> dict[str, Any]:
    """
    Send conversation history + tool schemas to Azure OpenAI.
    Returns either a text response or tool calls.
    """
    import time as _t
    _start = _t.time()

    client = _get_openai_client()
    deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    # ── Trim history to avoid sending huge payloads ──
    # Keep system + last 20 messages max.  Truncate long tool results.
    trimmed = _trim_history(messages)

    msg_count = len(trimmed)
    total_chars = sum(len(m.get("content", "") or "") for m in trimmed)
    activity.logger.info(f"[TIMING] LLM call: {msg_count} messages, ~{total_chars} chars")

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=trimmed,
            tools=tool_schemas,
            tool_choice="auto",
            temperature=0.2,
            max_completion_tokens=4096,
            timeout=60,  # seconds — prevent hanging
        )
    except Exception as e:
        elapsed = _t.time() - _start
        activity.logger.error(f"[TIMING] LLM call FAILED after {elapsed:.1f}s: {e}")
        return {"content": f"⚠️ LLM call failed: {type(e).__name__}: {str(e)[:200]}"}

    elapsed = _t.time() - _start
    message = response.choices[0].message

    if message.tool_calls:
        tools_requested = [tc.function.name for tc in message.tool_calls]
        activity.logger.info(f"[TIMING] LLM call took {elapsed:.1f}s → tools: {tools_requested}")
        return {
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
                for tc in message.tool_calls
            ]
        }

    activity.logger.info(f"[TIMING] LLM call took {elapsed:.1f}s → final text response ({len(message.content or '')} chars)")
    return {"content": message.content or ""}


def _trim_history(messages: list[dict], max_recent: int = 20, max_tool_result_len: int = 3000) -> list[dict]:
    """
    Keep the system message + the latest `max_recent` messages.
    Truncate oversized tool results so the LLM prompt stays small.
    IMPORTANT: Never split a tool_calls/tool pair — OpenAI requires every
    'tool' message to follow an 'assistant' message with 'tool_calls'.
    """
    # Separate system messages from the rest
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    # Keep only the most recent messages, but find a safe cut point
    if len(non_system) > max_recent:
        cut = len(non_system) - max_recent
        # Walk forward from the cut point to find a safe boundary:
        # never start with a 'tool' message (it needs its preceding assistant)
        while cut < len(non_system) and non_system[cut].get("role") == "tool":
            cut -= 1
        # Also don't start right after an assistant with tool_calls (keep that too)
        if cut > 0 and non_system[cut - 1].get("role") == "assistant" and non_system[cut - 1].get("tool_calls"):
            cut -= 1
        if cut < 0:
            cut = 0
        non_system = non_system[cut:]

    trimmed = []
    for msg in system_msgs + non_system:
        if msg.get("role") == "tool" and msg.get("content"):
            content = msg["content"]
            if len(content) > max_tool_result_len:
                # Try to parse and re-serialize with truncated data
                try:
                    data = json.loads(content)
                    if isinstance(data, dict):
                        # Truncate large string values, but preserve important keys
                        preserve_keys = {"staging_path", "file_path", "status", "instruction", "smell_type", "lines_affected"}
                        for key in list(data.keys()):
                            if key in preserve_keys:
                                continue
                            if isinstance(data[key], str) and len(data[key]) > 1500:
                                data[key] = data[key][:1500] + "\n... [truncated]"
                        content = json.dumps(data)
                    else:
                        content = content[:max_tool_result_len] + "\n... [truncated]"
                except (json.JSONDecodeError, TypeError):
                    content = content[:max_tool_result_len] + "\n... [truncated]"
                msg = {**msg, "content": content}
        trimmed.append(msg)

    return trimmed


# ──────────────────────────────────────────────
# ACTIVITY 2: RUN TOOL
# ──────────────────────────────────────────────

@activity.defn(name="run_tool")
async def run_tool(tool_name: str, tool_args: dict, workspace_path: str) -> dict[str, Any]:
    """Look up the tool handler by name and execute it."""
    handler = TOOL_HANDLERS.get(tool_name)

    if handler is None:
        return {"status": "error", "error": f"Unknown tool: '{tool_name}'. Available: {list(TOOL_HANDLERS.keys())}"}

    try:
        result = await handler(workspace_path=workspace_path, **tool_args)
        return result
    except Exception as e:
        return {"status": "error", "error": f"Tool '{tool_name}' error: {str(e)}"}
