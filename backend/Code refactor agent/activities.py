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
 
    from openai import AsyncAzureOpenAI
    from azure.identity import ClientSecretCredential
 
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    tenant_id = os.getenv("AZURE_TENANT_ID", "")
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")
 
    if tenant_id and client_id and client_secret:
        cred = ClientSecretCredential(tenant_id, client_id, client_secret)
        token = cred.get_token("https://cognitiveservices.azure.com/.default")
        client = AsyncAzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=token.token)
    else:
        client = AsyncAzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=os.getenv("AZURE_OPENAI_API_KEY", ""))
 
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
    # Keep system + messages fitting within context tokens.
    trimmed = _trim_history(messages)
 
    token_count = _get_token_count(trimmed)
    activity.logger.info(f"[TIMING] LLM call: {len(trimmed)} messages, {token_count} tokens")
 
    try:
        response = await client.chat.completions.create(
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
 
 
def _get_token_count(messages: list[dict], model: str = "gpt-4o") -> int:
    """Returns the total number of tokens in a list of messages."""
    try:
        import tiktoken
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
       
        num_tokens = 0
        for message in messages:
            num_tokens += 3  # base tokens per message
            for key, value in message.items():
                if value:
                    num_tokens += len(encoding.encode(str(value)))
        num_tokens += 3  # priming tokens
        return num_tokens
    except ImportError:
        # Fallback: rough char-based estimate (4 chars ≈ 1 token)
        total_chars = sum(len(str(v)) for m in messages for v in m.values() if v)
        return total_chars // 4
 
 
def _trim_history(messages: list[dict], max_tokens: int = 120000) -> list[dict]:
    """
    Keep the system message + as many recent messages as fit within `max_tokens`.
    Precisely counts tokens using tiktoken.
    """
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]
   
    # Prune from the bottom until we fit
    while len(non_system) > 1:
        current_tokens = _get_token_count(system_msgs + non_system)
        if current_tokens <= max_tokens:
            break
           
        # Drop oldest
        removed = non_system.pop(0)
       
        # Guard: Never leave a 'tool' message orphaned from its 'assistant' call
        if removed.get("role") == "assistant" and removed.get("tool_calls"):
             while non_system and non_system[0].get("role") == "tool":
                 non_system.pop(0)
       
        # Guard: If the head is now a 'tool' message, it's an orphan
        while non_system and non_system[0].get("role") == "tool":
            non_system.pop(0)
 
    return system_msgs + non_system
 
 
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