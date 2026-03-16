"""
tools.py — All tool handler functions in one place.

Tool schemas (what parameters each tool accepts) are now loaded from YAML files
in config/tools/*.yaml by config_loader.py.

This file contains only the actual Python handler functions that execute the tools.
The AI decides which tool to call, we look it up in TOOL_HANDLERS, and call it.

Handler name mapping — matches the YAML filenames exactly:
  github_inline_comment  ← config/tools/github_inline_comment.yaml
  read_file              ← config/tools/read_file.yaml
  write_file             ← config/tools/write_file.yaml
  list_files             ← config/tools/list_files.yaml
  ask_user               ← config/tools/ask_user.yaml
"""

import os
import base64
import aiohttp
from pathlib import Path


# ──────────────────────────────────────────────
# GITHUB HELPERS
# ──────────────────────────────────────────────

def _github_headers(token: str) -> dict:
    """Build GitHub API request headers."""
    headers = {"Accept": "application/vnd.github.v3+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def _get_default_branch(repo: str, token: str) -> str:
    """Ask GitHub which branch is the default for this repo."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.github.com/repos/{repo}", headers=_github_headers(token)) as r:
            if r.status == 200:
                data = await r.json()
                return data.get("default_branch", "main")
    return "main"


async def _get_repo_tree(repo: str, token: str) -> list[dict]:
    """Fetch the full recursive file tree of a GitHub repo."""
    branch = await _get_default_branch(repo, token)
    async with aiohttp.ClientSession() as session:
        url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
        async with session.get(url, headers=_github_headers(token)) as r:
            if r.status == 200:
                data = await r.json()
                return data.get("tree", [])
    return []


async def _resolve_file_path(repo: str, file_path: str, token: str) -> str | None:
    """
    Find the exact path of a file in the repo, even if only the filename (like 'App.jsx') was given.
    Returns the full path like 'frontend/src/pages/Home.jsx', or None if not found.
    """
    # Try direct fetch first
    async with aiohttp.ClientSession() as session:
        url = f"https://api.github.com/repos/{repo}/contents/{file_path.lstrip('/')}"
        async with session.get(url, headers=_github_headers(token)) as r:
            if r.status == 200:
                return file_path  # It already exists at the given path

    # Fallback: search the whole tree by filename
    tree = await _get_repo_tree(repo, token)
    blobs = [item["path"] for item in tree if item.get("type") == "blob"]

    # 1. Exact filename match (case-insensitive)
    exact = [p for p in blobs if p.split("/")[-1].lower() == file_path.lower().split("/")[-1]]
    if len(exact) == 1:
        print(f"[tools] Auto-discovered '{file_path}' → '{exact[0]}'")
        return exact[0]
    if len(exact) > 1:
        # Pick shallowest path (fewest folder levels)
        best = sorted(exact, key=lambda p: p.count("/"))[0]
        print(f"[tools] Multiple matches for '{file_path}', using: '{best}'")
        return best

    # 2. Substring match as last resort
    substr = [p for p in blobs if file_path.lower() in p.lower()]
    if substr:
        return sorted(substr, key=lambda p: p.count("/"))[0]

    return None


async def _fetch_github_file(repo: str, file_path: str, token: str) -> tuple[str | None, str | None]:
    """Fetch a file's content and SHA from GitHub. Returns (content, sha)."""
    async with aiohttp.ClientSession() as session:
        url = f"https://api.github.com/repos/{repo}/contents/{file_path.lstrip('/')}"
        async with session.get(url, headers=_github_headers(token)) as r:
            if r.status == 200:
                data = await r.json()
                content = base64.b64decode(data["content"]).decode("utf-8")
                return content, data["sha"]
    return None, None


async def _push_github_file(repo: str, file_path: str, content: str, sha: str, token: str) -> bool:
    """Commit updated file content back to GitHub."""
    payload = {
        "message": "docs: 🤖 Auto-edited via Simple Agent",
        "content": base64.b64encode(content.encode()).decode(),
        "sha": sha
    }
    async with aiohttp.ClientSession() as session:
        url = f"https://api.github.com/repos/{repo}/contents/{file_path.lstrip('/')}"
        async with session.put(url, headers=_github_headers(token), json=payload) as r:
            return r.status in (200, 201)


def _call_llm_for_comments(code: str, file_path: str, action: str, prompt: str) -> str:
    """
    Call Azure OpenAI to add/remove/update comments or summarize a file.
    Returns the modified code or a summary string.
    """
    from openai import AzureOpenAI
    from azure.identity import ClientSecretCredential

    tenant_id = os.getenv("AZURE_TENANT_ID", "")
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

    if tenant_id and client_id and client_secret:
        cred = ClientSecretCredential(tenant_id, client_id, client_secret)
        token_obj = cred.get_token("https://cognitiveservices.azure.com/.default")
        client = AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=token_obj.token)
    else:
        client = AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=os.getenv("AZURE_OPENAI_API_KEY", ""))

    if action == "add":
        system_msg = "You are a code documentation expert. Add clear, concise inline comments to every function, class, and complex logic block. Return ONLY the commented code — no markdown fences."
        user_msg = f"Add helpful inline comments to this {Path(file_path).suffix} file:\n\n{code}"
    elif action == "remove":
        system_msg = "You are a code cleanup tool. Remove ALL comments from the code. Return ONLY the clean code."
        user_msg = f"Remove all comments from this file:\n\n{code}"
    elif action == "summarize":
        system_msg = "You are a code review assistant. Provide a clear, structured summary of what this code does. NEVER use markdown code blocks (triple backticks) in your response."
        user_msg = f"{prompt or 'Summarize this file:'}\n\n{code}"
    elif action == "update":
        system_msg = "You are a code editing assistant. Apply the requested changes. Return ONLY the modified code."
        user_msg = f"Instructions: {prompt}\n\nCode:\n{code}"
    else:
        return code

    response = client.chat.completions.create(model=deployment, messages=[
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ])
    return response.choices[0].message.content or code


# ──────────────────────────────────────────────
# TOOL HANDLERS
# ──────────────────────────────────────────────

async def handle_github_inline_comment(
    file_path: str,
    action: str = "read",
    prompt: str = "",
    source: str = "local",
    github_repo: str = "",
    github_token: str = "",
    workspace_path: str = ".",
    **_
) -> dict:
    """
    Handle all GitHub file operations.
    Parameter names exactly match the fields defined in github_inline_comment.yaml.
    """
    token = github_token or os.getenv("GITHUB_TOKEN") or os.getenv("YOUR_GITHUB_ACCESS_TOKEN", "")
    repo = github_repo

    if source == "github":
        if not repo:
            return {"status": "error", "error": "github_repo is required when source='github'."}

        # For 'list' action — search the repo tree
        if action == "list":
            tree = await _get_repo_tree(repo, token)
            matched = [item["path"] for item in tree if file_path.lower() in item["path"].lower()]
            return {"status": "success", "files": matched[:30], "message": f"Found {len(matched)} items matching '{file_path}':\n" + "\n".join(f"- {p}" for p in matched[:30])}

        # Resolve and fetch the file
        resolved = await _resolve_file_path(repo, file_path, token)
        if not resolved:
            return {"status": "error", "error": f"Could not find '{file_path}' in repo '{repo}'. Try action='list' to browse."}

        raw_code, sha = await _fetch_github_file(repo, resolved, token)
        if raw_code is None:
            return {"status": "error", "error": f"Failed to fetch '{resolved}' from GitHub."}

        if action == "read":
            return {"status": "success", "file_path": resolved, "content": raw_code}

        # add/remove/summarize/update — call the LLM
        result_text = _call_llm_for_comments(raw_code, resolved, action, prompt)

        if action == "summarize":
            return {"status": "success", "file_path": resolved, "summary": result_text}

        pushed = await _push_github_file(repo, resolved, result_text, sha, token)
        if pushed:
            return {"status": "success", "file_path": resolved, "message": f"✅ '{resolved}' updated and pushed to GitHub."}
        return {"status": "error", "error": "Failed to push changes to GitHub."}

    else:
        # Local workspace file
        path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
        if not path.exists():
            return {"status": "error", "error": f"File not found: {path}"}
        raw_code = path.read_text(encoding="utf-8")

        if action == "read":
            return {"status": "success", "file_path": str(path), "content": raw_code}

        result_text = _call_llm_for_comments(raw_code, str(path), action, prompt)

        if action == "summarize":
            return {"status": "success", "file_path": str(path), "summary": result_text}

        path.write_text(result_text, encoding="utf-8")
        return {"status": "success", "file_path": str(path), "message": f"✅ '{path.name}' updated locally."}


async def handle_read_file(file_path: str, workspace_path: str = ".", **_) -> dict:
    """Read a local file."""
    path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
    if not path.exists():
        return {"status": "error", "error": f"File not found: {path}"}
    return {"status": "success", "content": path.read_text(encoding="utf-8")}


async def handle_write_file(file_path: str, content: str, workspace_path: str = ".", **_) -> dict:
    """Write content to a local file."""
    path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"status": "success", "message": f"File written: {path}"}


async def handle_list_files(directory: str = ".", workspace_path: str = ".", **_) -> dict:
    """List files in a local directory."""
    path = Path(directory) if Path(directory).is_absolute() else Path(workspace_path) / directory
    if not path.exists():
        return {"status": "error", "error": f"Directory not found: {path}"}
    files = [str(f.relative_to(path)) for f in sorted(path.rglob("*")) if f.is_file()]
    return {"status": "success", "files": files}


async def handle_ask_user(question: str, **_) -> dict:
    """Signals the workflow to pause and ask the user a question."""
    # The actual pausing is handled in workflow.py — this just returns the question
    return {"status": "ask_user", "question": question}


async def handle_rename_file(file_path: str, new_path: str, workspace_path: str = ".", **_) -> dict:
    """Rename or move a local file."""
    src = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
    dst = Path(new_path) if Path(new_path).is_absolute() else Path(workspace_path) / new_path
    if not src.exists():
        return {"status": "error", "error": f"File not found: {src}"}
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    return {"status": "success", "message": f"Renamed '{src}' → '{dst}'"}


async def handle_delete_file(file_path: str, workspace_path: str = ".", **_) -> dict:
    """Delete a local file."""
    path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
    if not path.exists():
        return {"status": "error", "error": f"File not found: {path}"}
    path.unlink()
    return {"status": "success", "message": f"Deleted '{path}'"}


# ──────────────────────────────────────────────
# TOOL DISPATCH TABLE
# Maps tool name (as defined in YAML filenames) -> handler function
# IMPORTANT: these keys must match the 'name:' field in each config/tools/*.yaml file
# ──────────────────────────────────────────────

TOOL_HANDLERS = {
    "github_inline_comment": handle_github_inline_comment,  # config/tools/github_inline_comment.yaml
    "read_file": handle_read_file,                          # config/tools/read_file.yaml
    "write_file": handle_write_file,                        # config/tools/write_file.yaml
    "rename_file": handle_rename_file,                      # config/tools/rename_file.yaml
    "delete_file": handle_delete_file,                      # config/tools/delete_file.yaml
    "list_files": handle_list_files,                        # config/tools/list_files.yaml
    "ask_user": handle_ask_user,                            # config/tools/ask_user.yaml
}
