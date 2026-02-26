# # process_automated_readme.py
# import os
# import base64
# import requests
# import datetime
# import pathlib
# from dotenv import load_dotenv

# from azure.identity import ClientSecretCredential
# from openai import AzureOpenAI

# # Import our summarizer helpers
# from repo_summarizer.tree_fetcher import fetch_full_repo
# from repo_summarizer.ast_graph_builder import build_combined_graph
# from repo_summarizer.file_ranker import rank_files
# from repo_summarizer.context_selector import select_snippets

# # Optional: your existing loader (if you have one)
# try:
#     from github_loader import load_github_repo
#     _HAS_GITHUB_LOADER = True
# except Exception:
#     load_github_repo = None
#     _HAS_GITHUB_LOADER = False

# load_dotenv()

# AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
# AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
# AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
# AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
# AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "")
# AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "")

# def get_azure_client() -> AzureOpenAI:
#     credential = ClientSecretCredential(
#         tenant_id=AZURE_TENANT_ID,
#         client_id=AZURE_CLIENT_ID,
#         client_secret=AZURE_CLIENT_SECRET
#     )
#     token = credential.get_token("https://cognitiveservices.azure.com/.default")
#     return AzureOpenAI(
#         azure_endpoint=AZURE_OPENAI_ENDPOINT,
#         api_version=AZURE_OPENAI_API_VERSION,
#         azure_ad_token=token.token
#     )

# def build_prompt(structure: str, code_snippets: str, repo_name: str = "") -> str:
#     repo_hint = f"This project is from the GitHub repository: **{repo_name}**\n" if repo_name else ""
#     return f"""
# You are an expert technical writer. Generate a professional, comprehensive README.md.
# ⚠️ CRITICAL INSTRUCTION: 
# - Base your description ONLY on the provided code snippets.
# - Do NOT use any information from previous versions of this project.
# - Don't take any knowledge from README file provided.
# - Ignore the repository name if it contradicts the code logic.
# {repo_hint}
# Project Structure:
# {structure}

# Key Source Files (excerpts):
# {code_snippets}

# Requirements — include ALL relevant sections:
# 1. Title & short description
# 2. Features list
# 3. Tech Stack
# 4. Installation Instructions
# 5. Usage Guide with examples
# 6. Environment Variables (if any .env or config seen)
# 7. API Reference (if endpoints detected)
# 8. Contributing
# 9. License

# Output strictly raw Markdown. Do NOT wrap in ```markdown blocks.
# """

# async def process_automated_readme(repo_name: str, token: str, include_all_files: bool = False):
#     """
#     repo_name: "owner/repo"
#     token: GitHub PAT (for file read/write)
#     include_all_files: if True, attempt to include all files in ranking (may be expensive)
#     """
#     print(f"Starting automated generation for {repo_name}...")

#     try:
#         # 1. Fetch full repo (file_map: path->content, file_tree: list(paths))
#         prefer_loader = _HAS_GITHUB_LOADER
#         file_map, file_tree = fetch_full_repo(repo_name, token, branch="main",
#                                              loader_fn=load_github_repo if _HAS_GITHUB_LOADER else None,
#                                              prefer_loader=prefer_loader)

#         if not file_tree:
#             print("No documents found to parse.")
#             return

#         # 2. Build structure text
#         structure = "\n".join([f"Repository: {repo_name} (branch: main)"] + file_tree)

#         # 3. Build AST/import graph (Python + JS heuristics)
#         graph = build_combined_graph(file_map)

#         # 4. Rank files (graph + heuristics)
#         ranked = rank_files(file_map, file_tree, graph, top_k=20, include_all=include_all_files)

#         # ranked is list of (path, score). When include_all_files=True, it's all files ordered.
#         # For context selection we want best-first ordering:
#         ranked_best_first = [(p, s) for p, s in ranked]

#         # 5. Select snippets (respect char budget)
#         MAX_CONTEXT_CHARS = 24_000
#         code_snippets = select_snippets(file_map, ranked_best_first, max_chars=MAX_CONTEXT_CHARS, lines_per_file=120)

#         prompt = build_prompt(structure, code_snippets, repo_name=repo_name)

#         # 6. Generate with Azure OpenAI
#         print("Calling Azure OpenAI...")
#         azure_client = get_azure_client()

#         response = azure_client.chat.completions.create(
#             model=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
#             messages=[
#                 {"role": "system", "content": "You are a helpful technical documentation assistant."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.7,
#             max_tokens=2500
#         )

#         raw_md = response.choices[0].message.content
#         md = raw_md.strip().removeprefix("```markdown").removeprefix("```").removesuffix("```")

#         # Force uniqueness with timestamp
#         timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         md += f"\n\n---\n> 🤖 *Last automated update: {timestamp}*"

#         # 7. Push README to GitHub
#         print("Pushing updated README to GitHub...")
#         owner, repo = repo_name.split("/", 1)
#         content_b64 = base64.b64encode(md.encode("utf-8")).decode("utf-8")

#         headers = {
#             "Authorization": f"token {token}",
#             "Accept": "application/vnd.github+json",
#             "User-Agent": "docugenius-agent",
#         }

#         get_url = f"https://api.github.com/repos/{owner}/{repo}/contents/README.md"
#         resp = requests.get(get_url, headers=headers, params={"ref": "main"})
#         sha = resp.json().get("sha") if resp.status_code == 200 else None

#         put_body = {"message": "Update README via DocuGenius", "content": content_b64, "branch": "main"}
#         if sha:
#             put_body["sha"] = sha

#         put_resp = requests.put(get_url, headers=headers, json=put_body)

#         if put_resp.status_code in (200, 201):
#             print(f"✅ Successfully updated README for {repo_name}!")
#         else:
#             print(f"❌ GitHub API Error: {put_resp.status_code} {put_resp.text}")

#     except Exception as e:
#         print(f"❌ Error during processing: {e}")

# process_automated_readme.py (updated snippet)
import os
import base64
import requests
import datetime
import pathlib
import json
import posixpath
from textwrap import indent
from dotenv import load_dotenv

from azure.identity import ClientSecretCredential
from openai import AzureOpenAI

from repo_summarizer.tree_fetcher import fetch_full_repo
from repo_summarizer.ast_graph_builder import build_combined_graph
from repo_summarizer.file_ranker import rank_files
from repo_summarizer.context_selector import select_snippets
from repo_summarizer.metadata_extractor import extract_all_metadata, format_metadata_block
from repo_summarizer.cache_manager import (
    load_cache, save_cache, merge_metadata,
)
from memory.preferences import load_preferences, format_preferences_prompt

# Optional: your existing loader (if you have one)
try:
    from github_loader import load_github_repo
    _HAS_GITHUB_LOADER = True
except Exception:
    load_github_repo = None
    _HAS_GITHUB_LOADER = False

load_dotenv()

AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "")
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "")

def get_azure_client() -> AzureOpenAI:
    credential = ClientSecretCredential(
        tenant_id=AZURE_TENANT_ID,
        client_id=AZURE_CLIENT_ID,
        client_secret=AZURE_CLIENT_SECRET
    )
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_ad_token=token.token
    )

def _preview_text(content: str, max_lines: int = 8, max_chars: int = 800) -> str:
    if not content:
        return "<empty>"
    lines = content.splitlines()
    preview = "\n".join(lines[:max_lines])
    if len(preview) > max_chars:
        preview = preview[:max_chars] + "…"
    if len(lines) > max_lines:
        preview += f"\n... ({len(lines)-max_lines} more lines)"
    return preview

def _print_file_map_snippets(file_map: dict, lines: int = 8):
    print("\n=== file_map (path -> preview) ===\n")
    for path in sorted(file_map.keys()):
        snippet = _preview_text(file_map.get(path, ""), max_lines=lines)
        print(f"{path}:\n{indent(snippet, '    ')}\n")

def _print_import_graph(graph: dict):
    printable = {k: sorted(list(v)) for k, v in graph.items()}
    print("\n=== import graph (path -> [imports]) ===\n")
    print(json.dumps(printable, indent=2))

def build_prompt(structure: str, code_snippets: str, metadata_block: str = "", preferences_block: str = "", repo_name: str = "") -> str:
    repo_hint = f"This project is from the GitHub repository: **{repo_name}**\n" if repo_name else ""
    metadata_section = ""
    if metadata_block:
        metadata_section = f"""

File Metadata (all files — functions, endpoints, schemas, env vars):
{metadata_block}
"""
    prefs_section = ""
    if preferences_block:
        prefs_section = f"""

{preferences_block}
"""
    return f"""
You are an expert technical writer. Generate a professional, comprehensive README.md.
⚠️ CRITICAL INSTRUCTION: 
- Base your description ONLY on the provided code snippets AND metadata.
- Do NOT use any information from previous versions of this project.
- Don't take any knowledge from README file provided.
- Ignore the repository name if it contradicts the code logic.
- Use the metadata section to cover ALL features, endpoints, and env vars accurately.
- Use the code snippets for deeper understanding of the most important files.
{repo_hint}
{prefs_section}
Project Structure:
{structure}
{metadata_section}
Key Source Files (excerpts of top-ranked files):
{code_snippets}

Requirements — include ALL relevant sections:
1. Title & short description
2. Features list
3. Tech Stack (use info from package.json / requirements.txt metadata)
4. Installation Instructions
5. Usage Guide with examples
6. Environment Variables (use the exact names from metadata)
7. API Reference (use the exact endpoints from metadata)
8. Contributing
9. License

Output strictly raw Markdown. Do NOT wrap in ```markdown blocks.
"""

async def process_automated_readme(
    repo_name: str,
    token: str,
    include_all_files: bool = False,
    show_mappings: bool = False,
    changed_files: set = None,
):
    """
    repo_name: "owner/repo"
    token: GitHub PAT (for file read/write)
    include_all_files: if True, include all files in ranking
    show_mappings: if True, print file_map previews and import graph to terminal
    changed_files: optional set of paths changed in this push (from webhook)
    """
    import json
    import os

    print(f"Starting automated generation for {repo_name}...")

    try:
        # ── 1. Fetch full repo ────────────────────────────────────────
        prefer_loader = _HAS_GITHUB_LOADER
        file_map, file_tree = fetch_full_repo(
            repo_name, token, branch="main",
            loader_fn=load_github_repo if _HAS_GITHUB_LOADER else None,
            prefer_loader=prefer_loader,
        )

        if not file_tree:
            print("No documents found to parse.")
            return

        # ── 2. Build import graph ─────────────────────────────────────
        graph = build_combined_graph(file_map)

        # ── 3. Diff-aware metadata extraction ─────────────────────────
        cache = load_cache(repo_name)
        cached_metadata = cache.get("file_metadata", {})

        # Use webhook diff: only re-extract changed files
        if changed_files:
            files_to_process = changed_files & set(file_map.keys())  # only files that still exist
            print(f"[cache] {len(files_to_process)} files changed (from webhook diff), re-extracting...")
            changed_file_map = {p: file_map[p] for p in files_to_process}
            fresh_metadata = extract_all_metadata(changed_file_map, verbose=True)
        elif cached_metadata:
            # No diff info but cache exists → nothing changed (shouldn't happen often)
            print("[cache] No changed files reported — using fully cached metadata.")
            fresh_metadata = {}
        else:
            # First run, no cache yet → extract everything
            print("[cache] No cache found — extracting metadata for all files...")
            fresh_metadata = extract_all_metadata(file_map, verbose=True)

        # Merge: cached (unchanged) + fresh (changed)
        file_metadata = merge_metadata(
            cached_metadata,
            fresh_metadata,
            current_file_tree=set(file_tree),
        )

        # Save updated cache
        import_graph_serializable = {k: sorted(list(v)) for k, v in graph.items()}
        cache_path = save_cache(repo_name, file_metadata, import_graph_serializable)
        print(f"[cache] Updated cache saved to {cache_path}")

        # Also write the human-readable mappings JSON
        try:
            os.makedirs("generated", exist_ok=True)
            mappings_path = f"generated/{repo_name.replace('/', '_')}_mappings.json"
            with open(mappings_path, "w", encoding="utf-8") as fh:
                json.dump({
                    "file_metadata": file_metadata,
                    "import_graph": import_graph_serializable
                }, fh, indent=2)
            print(f"[info] mappings written to {mappings_path}")
        except Exception as write_exc:
            print(f"[warning] failed to write mappings file: {write_exc}")

        # Format metadata for prompt
        metadata_block = format_metadata_block(file_metadata)

        if show_mappings:
            print("\n=== import graph (json view) ===")
            print(json.dumps(import_graph_serializable, indent=2))

            print("\n=== import graph (python-style with sets) ===")
            for k in sorted(graph.keys()):
                deps = graph.get(k, set())
                if deps:
                    dep_list = ", ".join(f"'{d}'" for d in sorted(deps))
                    print(f'  "{k}": {{{dep_list}}},')
                else:
                    print(f'  "{k}": set(),')
            print()

            _print_file_map_snippets(file_map, lines=8)

        # ── 4. Load user preferences ──────────────────────────────────
        prefs = load_preferences(repo_name)
        preferences_block = format_preferences_prompt(prefs)
        if preferences_block:
            print(f"[prefs] Loaded preferences for {repo_name}")

        # ── 5. Build structure + rank + select snippets ───────────────
        structure = "\n".join([f"Repository: {repo_name} (branch: main)"] + file_tree)

        ranked = rank_files(file_map, file_tree, graph, top_k=20, include_all=include_all_files)
        ranked_best_first = [(p, s) for p, s in ranked]

        RAW_CODE_CHARS = 14_000
        code_snippets = select_snippets(
            file_map, ranked_best_first, max_chars=RAW_CODE_CHARS, lines_per_file=120
        )

        prompt = build_prompt(
            structure, code_snippets,
            metadata_block=metadata_block,
            preferences_block=preferences_block,
            repo_name=repo_name,
        )

        # ── 6. Generate README with Azure OpenAI ──────────────────────
        print("Calling Azure OpenAI for README generation...")
        azure_client = get_azure_client()

        response = azure_client.chat.completions.create(
            model=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a helpful technical documentation assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2500
        )

        raw_md = response.choices[0].message.content
        md = raw_md.strip().removeprefix("```markdown").removeprefix("```").removesuffix("```")

        # Force uniqueness with timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        md += f"\n\n---\n> 🤖 *Last automated update: {timestamp}*"

        # ── 7. Push README to GitHub ──────────────────────────────────
        print("Pushing updated README to GitHub...")
        owner, repo = repo_name.split("/", 1)
        content_b64 = base64.b64encode(md.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "docugenius-agent",
        }

        get_url = f"https://api.github.com/repos/{owner}/{repo}/contents/README.md"
        resp = requests.get(get_url, headers=headers, params={"ref": "main"}, timeout=30)
        sha = resp.json().get("sha") if resp.status_code == 200 else None

        put_body = {"message": "Update README via DocuGenius", "content": content_b64, "branch": "main"}
        if sha:
            put_body["sha"] = sha

        put_resp = requests.put(get_url, headers=headers, json=put_body, timeout=30)

        if put_resp.status_code in (200, 201):
            print(f"✅ Successfully updated README for {repo_name}!")
        else:
            print(f"❌ GitHub API Error: {put_resp.status_code} {put_resp.text}")

    except Exception as e:
        print(f"❌ Error during processing: {e}")