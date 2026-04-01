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
        # Use LLM's workspace_path if it provided one, otherwise fall back to the workflow's path
        if "workspace_path" not in tool_args:
            tool_args["workspace_path"] = workspace_path
            
        result = await handler(**tool_args)
        return result
    except Exception as e:
        return {"status": "error", "error": f"Tool '{tool_name}' raised an exception: {str(e)}"}

# ──────────────────────────────────────────────
# ACTIVITY 3: GATHER CONTEXT (RAG PRE-PROCESSING)
# ──────────────────────────────────────────────

@activity.defn(name="gather_context")
async def gather_context(workspace_path: str, query: str) -> str:
    """
    RAG Pre-processing: Scans the workspace, extracts metadata, and semantically ranks files 
    against the query to provide crystal clear initial context to the agent.
    """
    import sys
    import os
    try:
        from parsers.tree_fetcher import fetch_local_repo
        from parsers.metadata_extractor import extract_all_metadata, format_metadata_block
        from parsers.ast_graph_builder import build_combined_graph
        from intelligence.file_ranker import rank_files
        from intelligence.semantic_ranker import semantic_rerank
    except ImportError as e:
        return f"Warning: Could not load local scanner modules ({e}). Running without pre-gathered context."

    if not os.path.exists(workspace_path):
        return f"Warning: Workspace path '{workspace_path}' does not exist locally."

    azure_client = _get_openai_client()
    
    # dynamically determine if the query specifically targets a sub-folder
    try:
        chat_deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        sys_msg = "You are a path extractor. Does the user's query specifically ask to analyze a certain directory/folder? If yes, output ONLY the folder name/path. If they ask about the whole project or don't specify a folder, output EXACTLY the character '.' (a single dot)."
        
        intent_resp = azure_client.chat.completions.create(
            model=chat_deployment,
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": query}],
            temperature=0, max_tokens=20
        )
        target_dir = intent_resp.choices[0].message.content.strip().strip("'\"")
        
        # If the LLM successfully extracted a folder and that folder exists
        if target_dir != "." and target_dir != "":
            potential_path = os.path.join(workspace_path, target_dir)
            if os.path.isdir(potential_path):
                workspace_path = potential_path
                print(f"[gather_context] Dynamically scoping scan to targeted folder: {target_dir}")
    except Exception as e:
        print(f"[gather_context] Folder scoping check failed, defaulting to full scan: {e}")

    # Start the actual scan against the resolved workspace_path
    file_map, file_tree = fetch_local_repo(workspace_path)
    if not file_tree:
        return "No files found in workspace."

    try:
        cached_metadata = extract_all_metadata(file_map)
        metadata_block = format_metadata_block(cached_metadata)
    except Exception as e:
        print(f"Metadata extraction failed: {e}")
        metadata_block = "Metadata unavailable."

    try:
        graph = build_combined_graph(file_map)
        ranked = rank_files(file_map, file_tree, graph, top_k=20, include_all=False)
    except Exception as e:
        print(f"Basic ranking failed: {e}")
        # Fallback to just alphabetical
        ranked = [(p, 1.0) for p in list(file_map.keys())[:20]]

    azure_client = _get_openai_client()
    deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")

    try:
        if query:
            ranked = semantic_rerank(
                ranked[:20], 
                file_map, 
                azure_client, 
                deployment, 
                query=query,
                top_k=5,
                cached_embeddings={}
            )
        else:
            ranked = ranked[:5]
    except Exception as e:
        print(f"Semantic reranking failed (possibly missing embeddings model): {e}")
        ranked = ranked[:5]

    context_str = f"Codebase Context ({workspace_path}):\n"
    context_str += f"Tree (first 30 items):\n{chr(10).join(file_tree[:30])}\n\n"
    context_str += f"Metadata:\n{metadata_block}\n\n"
    context_str += "Top Relevant Files based on request:\n"
    
    for p, _ in ranked:
        if p in file_map:
            content = file_map[p]
            context_str += f"\n--- {p} ---\n{content[:3000]}\n"
            
    return context_str
