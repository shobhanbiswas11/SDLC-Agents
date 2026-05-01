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
import re
import base64
import aiohttp
from pathlib import Path
import tempfile
import subprocess
import shutil


# ──────────────────────────────────────────────
# PATH SAFETY GUARD (prevents path traversal attacks)
# ──────────────────────────────────────────────

def _safe_path(file_path: str, workspace_path: str) -> Path:
    """
    Resolve a file path and ensure it stays within the workspace.
    Raises ValueError on path traversal attempts (e.g. ../../etc/passwd).
    """
    ws = Path(workspace_path).resolve()
    if Path(file_path).is_absolute():
        resolved = Path(file_path).resolve()
    else:
        resolved = (ws / file_path).resolve()
    # Guard: resolved path must be inside the workspace
    try:
        resolved.relative_to(ws)
    except ValueError:
        raise ValueError(
            f"Path traversal blocked: '{file_path}' resolves outside workspace '{ws}'."
        )
    return resolved



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


async def _push_github_file(repo: str, file_path: str, content: str, sha: str | None, token: str) -> bool:
    """Commit updated file content back to GitHub."""
    payload = {
        "message": "docs: 🤖 Auto-edited via Simple Agent",
        "content": base64.b64encode(content.encode()).decode()
    }
    if sha:
        payload["sha"] = sha
        
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

    is_md = file_path.lower().endswith(".md")
    
    if action == "comment":
        if is_md:
            system_msg = "You are a technical document editor. Improve the formatting, structure, and clarity of the markdown file. DO NOT include markdown fences (like ```markdown), and NEVER output conversational filler or refusals. Return ONLY the final raw markdown content."
            user_msg = f"Improve this Markdown file:\n\n{code}"
        else:
            system_msg = "You are a code documentation expert. Add clear, concise inline comments to every function, class, and complex logic block. Return ONLY the commented code — no markdown fences."
            user_msg = f"Add helpful inline comments to this {Path(file_path).suffix} file:\n\n{code}"
    elif action == "remove":
        system_msg = "You are a code cleanup tool. Remove ALL comments from the code. Return ONLY the clean code."
        user_msg = f"Remove all comments from this file:\n\n{code}"
    elif action == "summarize":
        system_msg = "You are a code review assistant. Provide a clear, structured summary of what this code does. NEVER use markdown code blocks (triple backticks) in your response."
        user_msg = f"{prompt or 'Summarize this file:'}\n\n{code}"
    elif action == "update":
        if is_md:
            system_msg = "You are a documentation editing assistant. Apply the requested changes to the markdown. Return ONLY the modified raw markdown without any markdown fences (like ```markdown), and absolutely NO conversational filler."
        else:
            system_msg = "You are a code editing assistant. Apply the requested changes. Return ONLY the modified code."
        user_msg = f"Instructions: {prompt}\n\nContent:\n{code}"
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

        if not resolved:
            if action == "create":
                resolved = file_path
                sha = None
                raw_code = ""
            else:
                return {"status": "error", "error": f"Could not find '{file_path}' in repo '{repo}'. Try action='create' to make a new file."}
        else:
            raw_code, sha = await _fetch_github_file(repo, resolved, token)
            if raw_code is None:
                return {"status": "error", "error": f"Failed to fetch '{resolved}' from GitHub."}

        if action == "read":
            return {"status": "success", "file_path": resolved, "content": raw_code}

        if action == "create":
            result_text = prompt  # create action just uses prompt as exact file content
        else:
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
    """Read a local file (path-traversal safe)."""
    try:
        path = _safe_path(file_path, workspace_path)
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    if not path.exists():
        return {"status": "error", "error": f"File not found: {path}"}
    return {"status": "success", "content": path.read_text(encoding="utf-8")}


async def handle_write_file(file_path: str, content: str, workspace_path: str = ".", **_) -> dict:
    """Write content to a local file (path-traversal safe)."""
    try:
        path = _safe_path(file_path, workspace_path)
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"status": "success", "file_path": str(path), "message": f"File written: {path}"}


async def handle_list_files(directory: str = ".", workspace_path: str = ".", **_) -> dict:
    """List files in a local directory (path-traversal safe)."""
    try:
        path = _safe_path(directory, workspace_path)
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    if not path.exists():
        return {"status": "error", "error": f"Directory not found: {path}"}
    files = [str(f.relative_to(path)) for f in sorted(path.rglob("*")) if f.is_file()]
    return {"status": "success", "files": files}


async def handle_ask_user(question: str, **_) -> dict:
    """Signals the workflow to pause and ask the user a question."""
    # The actual pausing is handled in workflow.py — this just returns the question
    return {"status": "ask_user", "question": question}


async def handle_rename_file(file_path: str, new_path: str, workspace_path: str = ".", **_) -> dict:
    """Rename or move a local file (path-traversal safe)."""
    try:
        src = _safe_path(file_path, workspace_path)
        dst = _safe_path(new_path, workspace_path)
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    if not src.exists():
        return {"status": "error", "error": f"File not found: {src}"}
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    return {"status": "success", "message": f"Renamed '{src}' → '{dst}'"}


async def handle_delete_file(file_path: str, workspace_path: str = ".", **_) -> dict:
    """Delete a local file (path-traversal safe)."""
    try:
        path = _safe_path(file_path, workspace_path)
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    if not path.exists():
        return {"status": "error", "error": f"File not found: {path}"}
    path.unlink()
    return {"status": "success", "message": f"Deleted '{path}'"}  


# ──────────────────────────────────────────────
# DOCUMENTATION DRAFTING TOOLS
# ──────────────────────────────────────────────

def _generate_docs_with_llm(system_msg: str, user_msg: str) -> str:
    """Call Azure OpenAI to generate documentation generically."""
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

    response = client.chat.completions.create(model=deployment, messages=[
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ])
    return response.choices[0].message.content or ""


def _get_folder_tree_string(folder_path: Path, max_depth: int = 3, current_depth: int = 0) -> str:
    """Helper to get a text representation of a directory tree."""
    if current_depth > max_depth or not folder_path.is_dir():
        return ""
    tree = []
    try:
        for p in folder_path.iterdir():
            if p.name.startswith(".") or "node_modules" in p.name or "__pycache__" in p.name or "venv" in p.name.lower():
                continue
            indent = "  " * current_depth
            if p.is_dir():
                tree.append(f"{indent}📂 {p.name}/")
                tree.append(_get_folder_tree_string(p, max_depth, current_depth + 1))
            else:
                tree.append(f"{indent}📄 {p.name}")
    except PermissionError:
        pass
    return "\n".join(filter(bool, tree))


async def handle_generate_readme(workspace_path: str = ".", **_) -> dict:
    wspath = Path(workspace_path)
    tree = _get_folder_tree_string(wspath, max_depth=2)
    
    # Try to grab some metadata from common package files
    context_files = []
    for f in ["package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod"]:
        p = wspath / f
        if p.exists():
            context_files.append(f"--- {f} ---\n{p.read_text(encoding='utf-8')[:1000]}")
            
    system_msg = "You are an expert technical writer. Generate a comprehensive, professional README.md for this project based on its structure and metadata. Output ONLY markdown."
    user_msg = f"Project tree:\n{tree}\n\nMetadata:\n{chr(10).join(context_files)}"
    
    res = _generate_docs_with_llm(system_msg, user_msg)
    return {"status": "success", "content": res}


async def handle_generate_api_docs(target_path: str, workspace_path: str = ".", **_) -> dict:
    path = Path(target_path) if Path(target_path).is_absolute() else Path(workspace_path) / target_path
    if not path.exists():
        return {"status": "error", "error": f"Path not found: {path}"}
        
    code_text = ""
    if path.is_file():
        code_text = path.read_text(encoding="utf-8")
    else:
        for p in list(path.rglob("*.py")) + list(path.rglob("*.ts")) + list(path.rglob("*.js")):
            if "node_modules" not in str(p):
                code_text += f"\n--- {p.name} ---\n{p.read_text(encoding='utf-8')[:2000]}"
                if len(code_text) > 30000: break
                
    system_msg = "You are an expert API documenter. Read the code and output detailed API documentation in Markdown format (endpoints, functions, parameters, return types)."
    user_msg = f"Code context:\n{code_text}"
    
    res = _generate_docs_with_llm(system_msg, user_msg)
    return {"status": "success", "content": res}


async def handle_expand_code_comments(file_path: str, workspace_path: str = ".", **_) -> dict:
    path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
    if not path.exists():
        return {"status": "error", "error": f"File not found: {path}"}
        
    code = path.read_text(encoding="utf-8")
    system_msg = "You are a code documentation engine. Add highly descriptive inline comments and docstrings to the code. Return ONLY the modified code, no markdown wrappers."
    
    res = _generate_docs_with_llm(system_msg, f"Add code comments to this file:\n\n{code}")
    return {"status": "success", "content": res}


async def handle_explain_folder_structure(folder_path: str, workspace_path: str = ".", **_) -> dict:
    path = Path(folder_path) if Path(folder_path).is_absolute() else Path(workspace_path) / folder_path
    if not path.exists() or not path.is_dir():
        return {"status": "error", "error": f"Folder not found or not a directory: {path}"}
        
    tree = _get_folder_tree_string(path, max_depth=3)
    system_msg = "You are a senior developer. Explain the following folder structure. For each directory, briefly define what it likely contains based on standard software patterns."
    
    res = _generate_docs_with_llm(system_msg, f"Folder structure:\n{tree}")
    return {"status": "success", "content": res}


async def handle_describe_architecture(workspace_path: str = ".", **_) -> dict:
    wspath = Path(workspace_path)
    
    import sys
    sys.path.append(str(Path(__file__).parent))
    from parsers.tree_fetcher import fetch_local_repo
    from parsers.ast_graph_builder import build_combined_graph

    try:
        file_map, file_tree = fetch_local_repo(str(wspath))
        graph = build_combined_graph(file_map)
        tree_str = "\n".join(file_tree[:500])
        edges = [f"{src} -> {dst}" for src, dests in graph.items() for dst in list(dests)[:20]]
        graph_str = "Import Dependencies:\n" + "\n".join(edges[:2000])
    except Exception as e:
        print(f"Warning: Failed to fetch RAG context for diagram: {e}")
        tree_str = _get_folder_tree_string(wspath, max_depth=3)
        graph_str = "No dependency graph available."

    system_msg = "You are a software architect. Analyze the folder structure and import graph to infer the project's high-level architecture. Provide a concise architectural overview in Markdown. You MUST also include a valid Mermaid.js graph visualization block (```mermaid ... ```) representing the architecture."
    res = _generate_docs_with_llm(system_msg, f"Project root structure:\n{tree_str}\n\n{graph_str}")
    return {"status": "success", "content": res}


async def handle_summarize_codebase(workspace_path: str = ".", **_) -> dict:
    wspath = Path(workspace_path)
    
    import sys
    sys.path.append(str(Path(__file__).parent))
    from parsers.tree_fetcher import fetch_local_repo
    from parsers.metadata_extractor import extract_all_metadata, format_metadata_block

    try:
        file_map, file_tree = fetch_local_repo(str(wspath))
        metadata = extract_all_metadata(file_map)
        metadata_block = format_metadata_block(metadata)
        tree_str = "\n".join(file_tree[:500])
    except Exception as e:
        print(f"Warning: Failed to fetch RAG context for summary: {e}")
        tree_str = _get_folder_tree_string(wspath, max_depth=3)
        metadata_block = "No deeper metadata available."

    system_msg = "You are a senior engineering manager. Provide a high-level summary of the entire codebase based on its structure and extracted metadata (imports, functions, APIs). Highlight the tech stack, main components, and likely purpose."
    res = _generate_docs_with_llm(system_msg, f"Project tree:\n{tree_str}\n\nMetadata Insights:\n{metadata_block}")
    return {"status": "success", "content": res}


async def handle_document_databases(schema_file_path: str, workspace_path: str = ".", **_) -> dict:
    path = Path(schema_file_path) if Path(schema_file_path).is_absolute() else Path(workspace_path) / schema_file_path
    if not path.exists():
        return {"status": "error", "error": f"Schema file not found: {path}"}
        
    schema = path.read_text(encoding="utf-8")
    system_msg = "You are a database administrator. Analyze the database schema and output a formatted Data Dictionary in Markdown, documenting tables, columns, relations, and primary/foreign keys."
    res = _generate_docs_with_llm(system_msg, f"Database schema:\n{schema}")
    return {"status": "success", "content": res}


async def handle_generate_diagrams(target_path: str, diagram_type: str, workspace_path: str = ".", **_) -> dict:
    path = Path(target_path) if Path(target_path).is_absolute() else Path(workspace_path) / target_path
    if not path.exists():
        return {"status": "error", "error": f"Path not found: {path}"}
        
    code = ""
    if path.is_file():
        code = path.read_text(encoding="utf-8")[:5000]
    else:
        import sys
        sys.path.append(str(Path(__file__).parent))
        from parsers.tree_fetcher import fetch_local_repo
        from parsers.ast_graph_builder import build_combined_graph
        try:
            file_map, file_tree = fetch_local_repo(str(path))
            graph = build_combined_graph(file_map)
            edges = [f"{src} -> {dst}" for src, dests in graph.items() for dst in list(dests)[:20]]
            code = f"Folder structure:\n{chr(10).join(file_tree[:500])}\n\nDependencies:\n{chr(10).join(edges[:2000])}"
        except Exception:
            code = _get_folder_tree_string(path, max_depth=2)
            
    system_msg = "You are a system architect. Generate ONLY a valid Mermaid.js diagram block for the requested diagram type. Use the structural dependencies provided to route the diagram. Do not include markdown code block syntax (like ```mermaid), just the raw mermaid code starting with 'graph', 'sequenceDiagram', etc."
    user_msg = f"Diagram Type: {diagram_type}\n\nContext:\n{code}"
    res = _generate_docs_with_llm(system_msg, user_msg)
    return {"status": "success", "content": res}


async def handle_improve_documentation(file_path: str, workspace_path: str = ".", **_) -> dict:
    path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
    if not path.exists():
        return {"status": "error", "error": f"File not found: {path}"}
        
    doc = path.read_text(encoding="utf-8")
    system_msg = "You are an expert technical editor. Improve the following markdown documentation. Make it clearer, more professional, and fix any grammar issues. Return ONLY the improved markdown."
    res = _generate_docs_with_llm(system_msg, f"Original Documentation:\n\n{doc}")
    return {"status": "success", "content": res}


# ──────────────────────────────────────────────
# GIT SSH TOOLS
# ──────────────────────────────────────────────

async def handle_git_push_ssh(ssh_private_key: str, commit_message: str = "docs: update documentation", files_to_add: str = ".", github_repo_url: str = "", workspace_path: str = ".", **_) -> dict:
    """Commit and push to a remote using an SSH private key."""
    path = Path(workspace_path)
    if not path.exists():
        return {"status": "error", "error": f"Workspace not found: {path}"}
        
    if not shutil.which("git"):
        return {"status": "error", "error": "git executable not found on the system."}

    fd, key_path = tempfile.mkstemp(text=True)
    try:
        # Write the private key
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(ssh_private_key)
            if not ssh_private_key.endswith('\n'):
                f.write('\n')
                
        # Prepare environment for SSH
        # Replace backslashes with forward slashes for OpenSSH on Windows
        ssh_cmd = f'ssh -i "{key_path.replace(chr(92), "/")}" -o StrictHostKeyChecking=no'
        env = os.environ.copy()
        env["GIT_SSH_COMMAND"] = ssh_cmd
        
        def run_git(args: list[str]) -> subprocess.CompletedProcess:
            return subprocess.run(["git"] + args, cwd=str(path), env=env, capture_output=True, text=True)

        if github_repo_url:
            res = run_git(["remote", "get-url", "origin"])
            if res.returncode == 0:
                run_git(["remote", "set-url", "origin", github_repo_url])
            else:
                run_git(["remote", "add", "origin", github_repo_url])
                
        add_res = run_git(["add", files_to_add])
        if add_res.returncode != 0:
            return {"status": "error", "error": f"Failed to git add: {add_res.stderr}"}
            
        commit_res = run_git(["commit", "-m", commit_message])
        if commit_res.returncode != 0 and "nothing to commit" not in commit_res.stdout:
            return {"status": "error", "error": f"Failed to git commit: {commit_res.stderr} {commit_res.stdout}"}
            
        branch_res = run_git(["branch", "--show-current"])
        current_branch = branch_res.stdout.strip() or "main"
        push_res = run_git(["push", "-u", "origin", current_branch])
        if push_res.returncode != 0:
            return {"status": "error", "error": f"Failed to git push: {push_res.stderr}"}
            
        return {"status": "success", "message": f"Successfully committed and pushed to origin/{current_branch} via SSH."}
        
    except Exception as e:
        return {"status": "error", "error": f"Exception during git operations: {str(e)}"}
    finally:
        try:
            os.remove(key_path)
        except Exception:
            pass

async def handle_git_push_token(github_token: str, commit_message: str = "docs: update documentation", files_to_add: str = ".", workspace_path: str = ".", **_) -> dict:
    """Commit and push to a remote using an HTTPS GitHub token."""
    path = Path(workspace_path)
    if not path.exists():
        return {"status": "error", "error": f"Workspace not found: {path}"}
        
    if not shutil.which("git"):
        return {"status": "error", "error": "git executable not found on the system."}

    try:
        def run_git(args: list[str], hide_error=False) -> subprocess.CompletedProcess:
            return subprocess.run(["git"] + args, cwd=str(path), capture_output=True, text=True)

        remote_url_res = run_git(["remote", "get-url", "origin"])
        if remote_url_res.returncode != 0:
            return {"status": "error", "error": "Could not find an 'origin' remote to push to."}
            
        # Get raw remote without https://
        remote_url = remote_url_res.stdout.strip().replace("https://", "")
        # Remove any existing token embed if it exists, like prev_token@github...
        if "@" in remote_url:
            remote_url = remote_url.split("@")[-1]
            
        auth_url = f"https://{github_token}@{remote_url}"
        
        # Setup git config user if not exists
        user_res = run_git(["config", "user.name"])
        if not user_res.stdout.strip():
            run_git(["config", "user.name", "DocuGenius"])
            run_git(["config", "user.email", "agent@docugenius.local"])
                
        add_res = run_git(["add", files_to_add])
        if add_res.returncode != 0:
            return {"status": "error", "error": f"Failed to git add: {add_res.stderr}"}
            
        commit_res = run_git(["commit", "-m", commit_message])
        
        branch_res = run_git(["branch", "--show-current"])
        current_branch = branch_res.stdout.strip() or "main"
        
        # Push directly using the inline auth URL so it doesn't leave the token in config
        push_res = run_git(["push", auth_url, current_branch])
        if push_res.returncode != 0:
            # Mask the token in error output so we don't accidentally leak it
            safe_err = push_res.stderr.replace(github_token, "***TOKEN***")
            safe_out = push_res.stdout.replace(github_token, "***TOKEN***")
            return {"status": "error", "error": f"Failed to git push with auth token: {safe_err} {safe_out}"}
            
        return {"status": "success", "message": f"Successfully committed and pushed to origin/{current_branch} via GitHub Token."}
        
    except Exception as e:
        safe_e = str(e).replace(github_token, "***TOKEN***")
        return {"status": "error", "error": f"Exception during token git operations: {safe_e}"}

async def handle_replace_code(file_path: str, replacements: str, workspace_path: str = ".", **_) -> dict:
    """Apply <<<< ==== >>>> style search and replace blocks to elegantly edit files."""
    path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
    if not path.exists():
        return {"status": "error", "error": f"File not found: {path}"}
        
    original_code = path.read_text(encoding="utf-8")
    
    import re
    pattern = re.compile(r"<<<<[ \t]*\n(.*?)\n====[ \t]*\n(.*?)\n>>>>", re.DOTALL)
    blocks = pattern.findall(replacements)
    
    if not blocks:
        return {"status": "error", "error": "No SEARCH/REPLACE blocks found. Use the exact format."}

    new_content = original_code
    for original_block, replace_block in blocks:
        if original_block not in new_content:
            return {"status": "error", "error": f"Search block not found exactly in file:\n{original_block[:150]}..."}
        new_content = new_content.replace(original_block, replace_block, 1)

    path.write_text(new_content, encoding="utf-8")
    return {"status": "success", "message": f"Successfully applied {len(blocks)} replacement(s) to '{path.name}'."}

# ──────────────────────────────────────────────
# GREP SEARCH
# ──────────────────────────────────────────────

async def handle_grep_search(pattern: str, directory: str = ".", file_pattern: str = "*.py",
                             context_lines: int = 2, workspace_path: str = ".", **_) -> dict:
    """Search for a regex pattern in files within the workspace."""
    try:
        search_dir = _safe_path(directory, workspace_path)
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    if not search_dir.exists():
        return {"status": "error", "error": f"Directory not found: {search_dir}"}

    try:
        compiled = re.compile(pattern)
    except re.error as e:
        return {"status": "error", "error": f"Invalid regex pattern: {e}"}

    matches = []
    for file_path in sorted(search_dir.rglob(file_pattern)):
        if not file_path.is_file():
            continue
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(lines):
            if compiled.search(line):
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = lines[start:end]
                matches.append({
                    "file": str(file_path.relative_to(Path(workspace_path).resolve())),
                    "line": i + 1,
                    "context": "\n".join(context),
                })
        if len(matches) >= 50:
            break

    return {"status": "success", "matches": matches, "total": len(matches)}


# ──────────────────────────────────────────────
# TOOL DISPATCH TABLE
# Maps tool name (as defined in YAML filenames) -> handler function
# IMPORTANT: these keys must match the 'name:' field in each config/tools/*.yaml file
# ──────────────────────────────────────────────

TOOL_HANDLERS = {
    "replace_code": handle_replace_code,                    # config/tools/replace_code.yaml
    "github_inline_comment": handle_github_inline_comment,  # config/tools/github_inline_comment.yaml
    "read_file": handle_read_file,                          # config/tools/read_file.yaml
    "write_file": handle_write_file,                        # config/tools/write_file.yaml
    "rename_file": handle_rename_file,                      # config/tools/rename_file.yaml
    "delete_file": handle_delete_file,                      # config/tools/delete_file.yaml
    "list_files": handle_list_files,                        # config/tools/list_files.yaml
    "ask_user": handle_ask_user,                            # config/tools/ask_user.yaml
    "generate_readme": handle_generate_readme,
    "generate_api_docs": handle_generate_api_docs,
    "expand_code_comments": handle_expand_code_comments,
    "explain_folder_structure": handle_explain_folder_structure,
    "describe_architecture": handle_describe_architecture,
    "summarize_codebase": handle_summarize_codebase,
    "document_databases": handle_document_databases,
    "generate_diagrams": handle_generate_diagrams,
    "improve_documentation": handle_improve_documentation,
    "git_push_ssh": handle_git_push_ssh,
    "git_push_token": handle_git_push_token,
    "grep_search": handle_grep_search,
}
