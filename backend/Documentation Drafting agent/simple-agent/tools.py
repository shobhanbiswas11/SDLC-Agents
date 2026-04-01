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
        tree_str = "\n".join(file_tree[:100])
        edges = [f"{src} -> {dst}" for src, dests in graph.items() for dst in dests[:10]]
        graph_str = "Import Dependencies:\n" + "\n".join(edges[:300])
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
        tree_str = "\n".join(file_tree[:150])
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
            edges = [f"{src} -> {dst}" for src, dests in graph.items() for dst in dests[:10]]
            code = f"Folder structure:\n{chr(10).join(file_tree[:100])}\n\nDependencies:\n{chr(10).join(edges[:300])}"
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
    "generate_readme": handle_generate_readme,
    "generate_api_docs": handle_generate_api_docs,
    "expand_code_comments": handle_expand_code_comments,
    "explain_folder_structure": handle_explain_folder_structure,
    "describe_architecture": handle_describe_architecture,
    "summarize_codebase": handle_summarize_codebase,
    "document_databases": handle_document_databases,
    "generate_diagrams": handle_generate_diagrams,
    "improve_documentation": handle_improve_documentation,
}
