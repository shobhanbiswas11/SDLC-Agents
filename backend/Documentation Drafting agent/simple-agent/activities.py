"""
activities.py — Temporal Activities.

Activities are plain Python functions that Temporal calls from the workflow.
They are allowed to do anything: network calls, disk I/O, call the LLM, etc.

We have exactly two activities:
  1. llm_call    — Send messages to Azure OpenAI and get tool calls or text back.
  2. run_tool    — Find the right tool handler and execute it.
"""

import json
import os
from typing import Any

from temporalio import activity

# Import tool handlers and schemas from our single tools.py file
from tools import TOOL_HANDLERS


# ──────────────────────────────────────────────        
# AZURE OPENAI CLIENT SETUP
# ──────────────────────────────────────────────

def _get_openai_client():
    """
    Build and return an Azure OpenAI client.
    Uses service principal auth (tenant/client/secret) if env vars are set,
    otherwise falls back to a plain API key.
    """
    from openai import AzureOpenAI
    from azure.identity import ClientSecretCredential

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    tenant_id = os.getenv("AZURE_TENANT_ID", "")
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")

    if tenant_id and client_id and client_secret:
        # Use Azure Active Directory (service principal) authentication
        cred = ClientSecretCredential(tenant_id, client_id, client_secret)
        token = cred.get_token("https://cognitiveservices.azure.com/.default")
        return AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=token.token)
    else:
        # Fall back to plain API key
        return AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=os.getenv("AZURE_OPENAI_API_KEY", ""))


# ──────────────────────────────────────────────
# ACTIVITY 1: LLM CALL
# ──────────────────────────────────────────────

@activity.defn(name="llm_call")
async def llm_call(messages: list[dict], tool_schemas: list[dict]) -> dict[str, Any]:
    """
    Sends the full conversation history + available tool schemas to Azure OpenAI.
    
    Returns either:
      {"content": "Here is my answer..."}           — if the AI gave a text reply
      {"tool_calls": [{"id": ..., "name": ..., "arguments": "..."}]}  — if the AI wants to use a tool
    """
    client = _get_openai_client()
    deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    response = client.chat.completions.create(
        model=deployment,
        messages=messages,
        tools=tool_schemas,
        tool_choice="auto",     # Let the AI decide whether to use a tool
        temperature=0.3,        # Lower = more focused, less creative
        max_completion_tokens=4096,
    )

    message = response.choices[0].message

    # Did the AI decide to call a tool?
    if message.tool_calls:
        print("AI wants to call tools:", [tc.function.name for tc in message.tool_calls]  )
        return {
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,   # This is the raw JSON string the AI generated
                }
                for tc in message.tool_calls
            ]
        
        }

    # No tool calls — the AI gave us a normal text response
    return {"content": message.content or ""}


# ──────────────────────────────────────────────
# ACTIVITY 2: RUN TOOL
# ──────────────────────────────────────────────

@activity.defn(name="run_tool")
async def run_tool(tool_name: str, tool_args: dict, workspace_path: str) -> dict[str, Any]:
    """
    Look up the tool handler by name and execute it.
    
    The tool_name comes directly from the AI's JSON output.
    The tool_args is the dictionary of arguments the AI wants to pass to the tool.
    workspace_path is injected automatically so tools know where to find local files.
    """
    handler = TOOL_HANDLERS.get(tool_name)

    if handler is None:
        return {"status": "error", "error": f"Unknown tool: '{tool_name}'. Available tools: {list(TOOL_HANDLERS.keys())}"}

    try:
        # Pass workspace_path as an extra kwarg — tool handlers that need it will use it
        result = await handler(workspace_path=workspace_path, **tool_args)
        return result
    except Exception as e:
        return {"status": "error", "error": f"Tool '{tool_name}' raised an exception: {str(e)}"}
