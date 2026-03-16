


import os
import re
import time
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

from parsers.tree_fetcher import fetch_full_repo, fetch_local_repo
from parsers.ast_graph_builder import build_combined_graph
from intelligence.file_ranker import rank_files
from intelligence.context_selector import select_snippets
from parsers.metadata_extractor import extract_all_metadata, format_metadata_block
from core.cache_manager import (
    load_cache, save_cache, merge_metadata,
)
from generators.section_detector import (
    detect_existing_sections, build_section_diff, format_section_diff_prompt,
    fetch_existing_readme_local, fetch_existing_readme_github,
)
from generators.diagram_generator import (
    build_mermaid_diagram, format_diagram_for_readme, build_diagram_summary,
)
from intelligence.semantic_ranker import semantic_rerank
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
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
USE_SEMANTIC_RANKING = os.environ.get("USE_SEMANTIC_RANKING", "false").lower() == "true"

def get_azure_client() -> AzureOpenAI:
    if AZURE_OPENAI_API_KEY.strip():
        return AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
            api_key=AZURE_OPENAI_API_KEY.strip(),
        )

    if not (AZURE_TENANT_ID.strip() and AZURE_CLIENT_ID.strip() and AZURE_CLIENT_SECRET.strip()):
        raise ValueError(
            "Azure auth is not configured. Set AZURE_OPENAI_API_KEY or set all of "
            "AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET."
        )

    try:
        credential = ClientSecretCredential(
            tenant_id=AZURE_TENANT_ID.strip(),
            client_id=AZURE_CLIENT_ID.strip(),
            client_secret=AZURE_CLIENT_SECRET.strip(),
        )
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        return AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_ad_token=token.token,
        )
    except Exception as e:
        raise ValueError(
            "Failed to initialize Azure OpenAI with Microsoft Entra credentials. "
            "Verify AZURE_CLIENT_ID is the Application (client) ID of an Entra App Registration, "
            "or set AZURE_OPENAI_API_KEY to use key-based auth. "
            f"Original error: {e}"
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

def build_prompt(
    structure: str, 
    code_snippets: str, 
    metadata_block: str = "", 
    preferences_block: str = "", 
    repo_name: str = "",
    custom_instructions: str = "",
    sections: list[str] = None,
    target_audience: str = "Mixed",
    section_diff_block: str = "",
    mermaid_diagram: str = "",
    existing_readme: str = "",
) -> str:
    repo_hint = f"This project is from the GitHub repository: **{repo_name}**\n" if repo_name else ""
    metadata_section = ""
    if metadata_block:
        metadata_section = f"""

File Metadata (all files — functions, endpoints, schemas, env vars):
{metadata_block}
"""

    section_diff_section = ""
    if section_diff_block:
        section_diff_section = section_diff_block

    diagram_section = ""
    if mermaid_diagram:
        diagram_section = f"""

====== ARCHITECTURE DIAGRAM ======
Embed EXACTLY the following Mermaid diagram block under an `## Architecture` section.
Do NOT modify any node names or edge definitions.

```mermaid
{mermaid_diagram}
```
=================================="""
    prefs_section = ""
    if preferences_block:
        prefs_section = f"""

{preferences_block}
"""
    custom_instruct_section = ""
    if custom_instructions:
        custom_instruct_section = f"""

====== USER CUSTOM INSTRUCTIONS ======
{custom_instructions}
======================================
"""

    audience_instructions = ""
    if target_audience == "Beginner Developers":
        audience_instructions = """
====== TARGET AUDIENCE: BEGINNER DEVELOPERS ======
CRITICAL REQUIREMENTS FOR THIS AUDIENCE:
1. EXPLAIN EVERYTHING: Assume the reader has very little experience with this tech stack.
2. TONE: Friendly, welcoming, encouraging, and easy to read.
3. SETUP: Break down the Installation and Usage into extremely detailed, baby-step instructions. Do NOT skip any steps (e.g., explain how to create virtual environments, etc).
4. ARCHITECTURE: Keep architecture explanations very high-level and easy to digest.
==================================================
"""
    elif target_audience == "Advanced Engineers":
        audience_instructions = """
====== TARGET AUDIENCE: ADVANCED/SENIOR ENGINEERS ======
CRITICAL REQUIREMENTS FOR THIS AUDIENCE:
1. NO FLUFF: Skip obvious setups and hand-holding. They already know the basics.
2. TONE: Dry, highly technical, concise, and direct.
3. FOCUS: Heavily focus on System Architecture, scaling, Design Patterns, Advanced Configuration, and API edge-cases.
4. DEEP DIVE: Go deep into the technical specifications and how the core engine works under the hood based on the provided code.
========================================================
"""
    elif target_audience == "End Users":
        audience_instructions = """
====== TARGET AUDIENCE: NON-TECHNICAL END USERS ======
CRITICAL REQUIREMENTS FOR THIS AUDIENCE:
1. NO CODE: Do NOT show any code snippets, API endpoints, or database configurations.
2. TONE: Plain English, strictly business/product focused.
3. FOCUS: Only explain WHAT the product does and the features it provides to the end user.
4. EXCLUSIONS: Skip the 'Installation Instructions', 'Tech Stack', and 'API Reference' sections entirely.
======================================================
"""
    if custom_instructions:
        requirements_section = f"""
Requirements:
You MUST follow the USER CUSTOM INSTRUCTIONS above. 
If they contradict the default structure below, the custom instructions OVERRIDE them.
"""
    else:
        requirements_section = "Requirements:\n"

    if sections and len(sections) > 0:
        requirements_section += "\nGenerate the following sections if they match the TARGET AUDIENCE (skip any that contradict the audience):\n"
        for idx, sec in enumerate(sections, 1):
            requirements_section += f"{idx}. {sec}\n"
        requirements_section += "\nDo NOT generate any other sections unless specifically requested in the User Custom Instructions.\n"
    else:
        requirements_section += """
Default Structure (Include ALL of these):
1. Title & short description
2. Features list
3. Tech Stack
4. Installation Instructions
5. Usage Guide
6. Environment Variables
7. API Reference
8. Contributing
9. License
"""

    existing_readme_section = ""
    if existing_readme:
        existing_readme_section = f"""

====== EXISTING README CONTENT ======
{existing_readme}
=====================================
"""

    return f"""
You are an expert technical writer. Generate a professional, comprehensive README.md.
⚠️ CRITICAL INSTRUCTION: 
- Base your description on the provided code snippets AND metadata.
- If an EXISTING README CONTENT is provided below, PRESERVE its existing sections exactly as they are written unless the code snippets/metadata clearly contradict them.
- Only generate FRESH content for the sections listed as "Missing" in the SMART SECTION DETECTION block.
- Ignore the repository name if it contradicts the code logic.
- For the API Reference section, you MUST EXPLICITLY LIST EVERY SINGLE individual API endpoint (e.g., GET /users, POST /login) found in the metadata block. Do NOT summarize or group them at a high level. Write out the exact routes and their purposes.
- Use the code snippets for deeper understanding of the most important files.
{audience_instructions}
{repo_hint}
{prefs_section}
{custom_instruct_section}
{section_diff_section}
{diagram_section}
Project Structure:
{structure}
{metadata_section}
Key Source Files (excerpts of top-ranked files):
{code_snippets}

{requirements_section}
{existing_readme_section}

Output strictly raw Markdown. Do NOT wrap in ```markdown blocks.
"""

async def process_automated_readme(
    repo_name: str = "",
    token: str = "",
    local_path: str = None,
    include_all_files: bool = False,
    show_mappings: bool = False,
    changed_files: set = None,
    custom_instructions: str = None,
    sections: list[str] = None,
    target_audience: str = "Mixed",
    auto_commit: bool = True,
    progress_callback = None,
):
    """
    repo_name: "owner/repo" (ignored if local_path is provided)
    token: GitHub PAT (for file read/write, ignored if local_path is provided)
    local_path: absolute or relative path to a local directory
    include_all_files: if True, include all files in ranking
    show_mappings: if True, print file_map previews and import graph to terminal
    changed_files: optional set of paths changed in this push (from webhook)
    progress_callback: optional async function to receive progress updates
    """
    import json
    import os

    import asyncio
    
    # Identify target name for logs
    target_name = local_path if local_path else repo_name
    
    print(f"Starting automated generation for {target_name}...")
    if progress_callback:
        await progress_callback({"step": "fetching", "status": "running", "message": f"Fetching repository: {target_name}..."})
        await asyncio.sleep(0.01)

    try:
        # ── 1. Fetch full repo ────────────────────────────────────────
        if local_path:
            file_map, file_tree = fetch_local_repo(local_path)
        else:
            prefer_loader = _HAS_GITHUB_LOADER
            file_map, file_tree = fetch_full_repo(
                repo_name, token, branch="main",
                loader_fn=load_github_repo if _HAS_GITHUB_LOADER else None,
                prefer_loader=prefer_loader,
            )

        if not file_tree:
            print("No documents found to parse.")
            if progress_callback:
                await progress_callback({"step": "fetching", "status": "error", "message": "No documents found to parse."})
            return
            
        if progress_callback:
            await progress_callback({"step": "fetching", "status": "done", "message": f"Fetched {len(file_map)} files."})
            await progress_callback({"step": "section_scan", "status": "running", "message": "Scanning existing README for sections..."})
            await asyncio.sleep(0.01)

        # ── 1b. Smart Section Detection ────────────────────────────────────────
        existing_readme = None
        section_diff_block = ""
        try:
            if local_path:
                existing_readme = fetch_existing_readme_local(local_path)
            else:
                existing_readme = fetch_existing_readme_github(repo_name, token)
            if existing_readme:
                existing_sections = detect_existing_sections(existing_readme)
                diff = build_section_diff(existing_sections, sections)
                section_diff_block = format_section_diff_prompt(diff)
                print(f"[section_scan] Found {len(existing_sections)} existing sections: {existing_sections}")
                if progress_callback:
                    await progress_callback({
                        "step": "section_scan",
                        "status": "done",
                        "message": f"Found {len(existing_sections)} existing sections — {len(diff.get('missing', []))} to regenerate.",
                    })
            else:
                print("[section_scan] No existing README found — generating fresh.")
                if progress_callback:
                    await progress_callback({"step": "section_scan", "status": "done", "message": "No existing README — generating fresh."})
        except Exception as scan_err:
            print(f"[section_scan] Warning: {scan_err}")
            if progress_callback:
                await progress_callback({"step": "section_scan", "status": "done", "message": "Section scan skipped."})

        await asyncio.sleep(0.01)
        if progress_callback:
            await progress_callback({"step": "parsing", "status": "running", "message": "Building import graph and ranking files..."})
            await asyncio.sleep(0.01)

        # ── 2. Build import graph ─────────────────────────────────────
        graph = build_combined_graph(file_map)
        
        if progress_callback:
            await progress_callback({"step": "parsing", "status": "done", "message": "AST and import graph built successfully."})
            await progress_callback({"step": "caching", "status": "running", "message": "Extracting and merging metadata cache..."})
            await asyncio.sleep(0.01)

        # ── 3. Diff-aware metadata extraction ─────────────────────────
        # For cache identification
        cache_key = target_name.replace("/", "_").replace("\\", "_")
        cache = load_cache(cache_key)
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
        cache_path = save_cache(cache_key, file_metadata, import_graph_serializable)
        print(f"[cache] Updated cache saved to {cache_path}")
        if progress_callback:
            await progress_callback({"step": "caching", "status": "done", "message": "Metadata extracted and cached."})
            await progress_callback({"step": "generating", "status": "running", "message": "Building architecture diagram..."})
            await asyncio.sleep(0.01)

        # ── 3b. Build Mermaid architecture diagram ────────────────────
        try:
            diagram_summary = build_diagram_summary(graph)
            mermaid_diagram = diagram_summary.get("mermaid", "")
            if mermaid_diagram:
                print(f"[diagram] Built diagram: {diagram_summary['node_count']} nodes, {diagram_summary['edge_count']} edges.")
        except Exception as diag_err:
            print(f"[diagram] Warning: {diag_err}")
            diagram_summary = {}
            mermaid_diagram = ""

        # Also write the human-readable mappings JSON
        try:
            os.makedirs("generated", exist_ok=True)
            mappings_path = f"generated/{cache_key}_mappings.json"
            with open(mappings_path, "w", encoding="utf-8") as fh:
                json.dump({
                    "file_metadata": file_metadata,
                    "import_graph": import_graph_serializable,
                    "diagram": diagram_summary,
                }, fh, indent=2)
            print(f"[info] mappings written to {mappings_path}")
        except Exception as write_exc:
            print(f"[warning] failed to write mappings file: {write_exc}")

        # (Metadata block formatting moved below file ranking to save tokens)
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
        prefs = load_preferences(target_name)
        preferences_block = format_preferences_prompt(prefs)
        if preferences_block:
            print(f"[prefs] Loaded preferences for {target_name}")

        # ── 5. Build rank + select snippets ───────────────
        ranked = rank_files(file_map, file_tree, graph, top_k=500, include_all=include_all_files)
        ranked_best_first = [(p, s) for p, s in ranked]

        # Build structure string using ONLY the top ranked files so it doesn't feed the LLM 100 random junk files
        top_ranked_paths = [p for p, s in ranked_best_first]
        if len(file_tree) > 100:
            prompt_tree = top_ranked_paths[:100] + [f"... and {len(file_tree) - 100} more files omitted for brevity"]
        else:
            prompt_tree = file_tree
        structure = "\n".join([f"Repository: {target_name} (branch: main)"] + prompt_tree)

        # ── Semantic re-ranking (opt-in) ──────────────────────────────────────
        azure_client = get_azure_client()
        if USE_SEMANTIC_RANKING:
            try:
                print("[semantic_ranker] Semantic ranking enabled — re-ranking candidates...")
                if progress_callback:
                    await progress_callback({"step": "generating", "status": "running", "message": "Semantic re-ranking files with embeddings..."})
                ranked_best_first = semantic_rerank(
                    ranked_best_first,
                    file_map,
                    azure_client,
                    AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                    top_k=500,
                )
            except Exception as sr_err:
                print(f"[semantic_ranker] Failed ({sr_err}), falling back to heuristic ranking.")
                ranked_best_first = ranked_best_first[:500]

        RAW_CODE_CHARS = 24_000 # Set raw code limit to 10k
        # Increased to top 50 files based on user preference to maximize metadata context
        ranked_best_first = ranked_best_first[:500]
        
        code_snippets = select_snippets(
            file_map, ranked_best_first, max_chars=RAW_CODE_CHARS, lines_per_file=120
        )

        print(f"[metadata_extractor] Filtering massive metadata block down to top {len(ranked_best_first)} files...")
        top_ranked_paths = {p for p, s in ranked_best_first}
        capped_metadata = {k: v for k, v in file_metadata.items() if k in top_ranked_paths}
        metadata_block = format_metadata_block(capped_metadata)


        prompt = build_prompt(
            structure, code_snippets,
            metadata_block=metadata_block,
            preferences_block=preferences_block,
            repo_name=target_name,
            custom_instructions=custom_instructions,
            sections=sections,
            target_audience=target_audience,
            section_diff_block=section_diff_block,
            mermaid_diagram=mermaid_diagram,
            existing_readme=existing_readme,
        )

        # ── 6. Generate README with Azure OpenAI (with retry on 429) ───
        print("Calling Azure OpenAI for README generation...")

        MAX_RETRIES = 4
        BASE_WAIT = 30  # seconds — fallback if we can't parse the retry-after value

        response = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = azure_client.chat.completions.create(
                    model=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
                    messages=[
                        {"role": "system", "content": "You are a helpful technical documentation assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2500,
                    stream=True
                )
                break  # success — exit the retry loop
            except Exception as llm_err:
                err_str = str(llm_err)
                is_rate_limit = "429" in err_str or "RateLimitReached" in err_str or "rate limit" in err_str.lower()
                if is_rate_limit and attempt < MAX_RETRIES:
                    # Try to extract the suggested wait time from the error message
                    wait_match = re.search(r'retry after (\d+) second', err_str, re.IGNORECASE)
                    wait_secs = int(wait_match.group(1)) + 2 if wait_match else BASE_WAIT * attempt
                    print(f"[rate_limit] 429 received (attempt {attempt}/{MAX_RETRIES}). "
                          f"Waiting {wait_secs}s before retry...")
                    time.sleep(wait_secs)
                else:
                    # Non-rate-limit error, or exhausted retries — re-raise
                    raise

        if response is None:
            raise RuntimeError("Azure OpenAI returned no response after all retries.")

        raw_md_chunks = []
        for chunk in response:
            if len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    raw_md_chunks.append(delta.content)
                    if progress_callback:
                        await progress_callback({
                            "step": "generating",
                            "status": "running",
                            "chunk": delta.content
                        })

        raw_md = "".join(raw_md_chunks).strip()
        if raw_md.startswith("```markdown") and raw_md.endswith("```"):
            md = raw_md[11:-3].strip()
        elif raw_md.startswith("```") and raw_md.endswith("```"):
            md = raw_md[3:-3].strip()
        else:
            md = raw_md
        # Force uniqueness with timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        md += f"\n\n---\n> 🤖 *Last automated update: {timestamp}*"
        
        if progress_callback:
            await progress_callback({"step": "generating", "status": "done", "message": "README generated successfully."})
            if auto_commit:
                await progress_callback({"step": "pushing", "status": "running", "message": "Saving README..."})
            await asyncio.sleep(0.01)

        # ── 7. Push README to GitHub or Save Locally ─────────────────
        if not auto_commit:
            print("Preview complete. Auto-commit is disabled.")
            if progress_callback:
                await progress_callback({
                    "step": "done",
                    "status": "done",
                    "message": "Preview generated successfully. Waiting for manual commit.",
                    "file_url": None,
                    "diagram": mermaid_diagram,
                    "semantic_ranking": USE_SEMANTIC_RANKING,
                })
            return md
        if local_path:
            await push_readme_to_target(md, repo_name=repo_name, token=token, local_path=local_path, progress_callback=progress_callback)
        else:
            await push_readme_to_target(md, repo_name=repo_name, token=token, local_path="", progress_callback=progress_callback)

    except Exception as e:
        print(f"❌ Error during processing: {e}")
        if progress_callback:
            await progress_callback({"step": "error", "status": "error", "message": f"Error: {e}"})

async def push_readme_to_target(
    md_content: str,
    repo_name: str,
    token: str,
    local_path: str = "",
    progress_callback=None
):
    """
    Helper function to save the markdown content locally or push it to GitHub.
    """
    if local_path:
        print(f"Saving generated README to {local_path}...")
        readme_dest = os.path.join(local_path, "README.md")
        # Create a backup if README.md exists
        if os.path.exists(readme_dest):
            backup_dest = os.path.join(local_path, "README.md.backup")
            import shutil
            shutil.copy2(readme_dest, backup_dest)
            print(f"Created backup at {backup_dest}")
            
        with open(readme_dest, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"✅ Successfully wrote README to {readme_dest}!")
        
        if progress_callback:
            await progress_callback({"step": "pushing", "status": "done", "message": "README saved locally!", "file_url": f"file://{readme_dest}"})
            await progress_callback({"step": "done", "status": "done", "message": "All tasks completed.", "file_url": f"file://{readme_dest}"})
            
    else:
        print("Pushing updated README to GitHub...")
        owner, repo = repo_name.split("/", 1)
        content_b64 = base64.b64encode(md_content.encode("utf-8")).decode("utf-8")

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
            file_url = f"https://github.com/{owner}/{repo}/blob/main/README.md"
            if progress_callback:
                await progress_callback({"step": "pushing", "status": "done", "message": "README pushed successfully!", "file_url": file_url})
                await progress_callback({"step": "done", "status": "done", "message": "All tasks completed.", "file_url": file_url})
        else:
            print(f"❌ GitHub API Error: {put_resp.status_code} {put_resp.text}")
            if progress_callback:
                await progress_callback({"step": "pushing", "status": "error", "message": f"GitHub API Error: {put_resp.text}"})


        