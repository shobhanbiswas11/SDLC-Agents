# app/main.py

import json
import os
import shutil
import subprocess
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.services.agent_service import (
    EXTENSION_MAP,
    analyze_code,
    detect_language,
    fix_all_violations,
    get_all_supported_extensions,
)
from app.services.ai_service import generate_fix
from app.services.diff_service import generate_diff
from app.services.repo_service import clone_repository, list_remote_branches
from app.services.scan_service import extract_snippet, run_flake8

app = FastAPI(title="AI Coding Standards Enforcer — Multi-Language Agent")


# =========================================================
# CORS Configuration
# =========================================================

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# Request Models
# =========================================================


class ScanRequest(BaseModel):
    repo_url: str = ""
    local_path: str = ""


class AnalyzeRequest(BaseModel):
    """Request for live code analysis — the agent endpoint."""

    code: str
    language: str  # python, cpp, java, javascript, typescript, go, rust


class FixAllRequest(BaseModel):
    """Request to fix all violations in user-provided code."""

    code: str
    language: str
    violations: list = []  # optional — if empty, agent will re-analyze first


class CloneRepoRequest(BaseModel):
    """Request to clone a repo and list all source files for the editor."""

    repo_url: str = ""
    local_path: str = ""
    branch: str = ""  # optional: specific branch to checkout


class ApplyLintersRequest(BaseModel):
    repo_path: str


# =========================================================
# Health Check
# =========================================================


@app.get("/")
def health():
    return {"status": "Backend running — Multi-Language Agent Mode"}


# =========================================================
# Supported Languages
# =========================================================


@app.get("/languages")
def supported_languages():
    """Return list of supported languages with their info."""
    from app.llm.agent_prompts import LANGUAGE_STANDARDS

    languages = []
    for key, info in LANGUAGE_STANDARDS.items():
        languages.append(
            {
                "key": key,
                "name": info["name"],
                "standards": info["standards"],
                "categories": info["categories"],
            }
        )
    return {"languages": languages}


# =========================================================
# 📂 Clone Repo → File Tree for Live Editor
# =========================================================


SKIP_DIRS = {
    "__pycache__", "node_modules", ".git", "venv", ".venv",
    "target", "build", "dist", "bin", "obj", "vendor", "pkg",
    ".idea", ".vscode", ".gradle", ".mvn",
}


@app.post("/repo-files")
def get_repo_files(request: CloneRepoRequest):
    """
    Clone a GitHub repo (or use a local path) and return all
    supported source files with contents and detected language.
    Designed to feed the Live Editor's file tree.
    Optionally accepts a `branch` to clone a specific branch.
    """
    try:
        if request.local_path:
            local = Path(request.local_path)
            if not local.exists() or not local.is_dir():
                raise HTTPException(
                    status_code=400,
                    detail="Local path does not exist or is not a directory.",
                )
            repo_path = str(local.resolve())
        elif request.repo_url:
            branch = request.branch if request.branch else None
            repo_path = clone_repository(request.repo_url, branch=branch)
        else:
            raise HTTPException(
                status_code=400,
                detail="Please provide a GitHub URL or a local directory path.",
            )

        supported_exts = get_all_supported_extensions()
        files = {}
        repo = Path(repo_path)

        for root, dirs, filenames in os.walk(repo_path):
            # Skip non-source dirs
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d not in SKIP_DIRS
            ]
            for fname in sorted(filenames):
                fpath = Path(root) / fname
                ext = fpath.suffix.lower()
                if ext not in supported_exts:
                    continue

                rel = str(fpath.relative_to(repo))
                lang = detect_language(fname)

                try:
                    content = fpath.read_text(errors="replace")
                    # Skip very large files (>100KB)
                    if len(content) > 100_000:
                        content = content[:100_000] + "\n\n// ... (file truncated — too large for editor)"
                except Exception:
                    content = "// Could not read file"

                files[rel] = {
                    "content": content,
                    "language": lang or "plaintext",
                    "size_bytes": fpath.stat().st_size if fpath.exists() else 0,
                }

        return {
            "repo_path": repo_path,
            "total_files": len(files),
            "files": files,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# 🌿 List Remote Branches
# =========================================================


class RepoBranchesRequest(BaseModel):
    """Request to list branches of a remote repository."""
    repo_url: str


@app.post("/repo-branches")
def get_repo_branches(request: RepoBranchesRequest):
    """
    List all branches of a remote GitHub repository.
    Returns branch names and short SHAs, sorted with common
    default branches (main, master, develop) first.
    """
    try:
        if not request.repo_url.strip():
            raise HTTPException(status_code=400, detail="Repository URL is required.")

        branches = list_remote_branches(request.repo_url)
        return {
            "branches": branches,
            "total": len(branches),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# 🤖 AGENT: Live Code Analysis (NEW)
# =========================================================


@app.post("/analyze")
def analyze_code_endpoint(request: AnalyzeRequest):
    """
    AI Agent analyzes code for coding standard violations.
    Works for Python, C++, Java, JavaScript, TypeScript, Go, Rust.

    This is the AGENT endpoint — the AI autonomously identifies
    violations without relying on external linters.
    """
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty.")

    language = request.language.lower()

    # Validate language
    from app.llm.agent_prompts import get_supported_languages

    if language not in get_supported_languages():
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {language}. Supported: {', '.join(get_supported_languages())}",
        )

    result = analyze_code(request.code, language)

    return {
        "language": language,
        "violations": result["violations"],
        "summary": result["summary"],
    }


# =========================================================
# 🤖 AGENT: Fix All Violations (NEW)
# =========================================================


@app.post("/fix")
def fix_code_endpoint(request: FixAllRequest):
    """
    AI Agent fixes all violations in the provided code.
    If no violations are provided, re-analyzes first.
    """
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty.")

    language = request.language.lower()

    violations = request.violations
    if not violations:
        # Agent mode: re-analyze to find violations
        analysis = analyze_code(request.code, language)
        violations = analysis.get("violations", [])

    if not violations:
        return {
            "explanation": "No violations found — code is already clean!",
            "fixed_code": request.code,
            "diff": "",
        }

    result = fix_all_violations(request.code, language, violations)
    diff = generate_diff(request.code, result["fixed_code"])

    return {
        "explanation": result["explanation"],
        "fixed_code": result["fixed_code"],
        "diff": diff,
    }


# =========================================================
# Scan Repository (Enhanced for Multi-Language)
# =========================================================


@app.post("/scan")
def scan_repo(request: ScanRequest):
    """
    Stream scan progress as newline-delimited JSON.
    Now supports multi-language analysis using the AI agent.
    Each line is either:
      {"type": "log",    "message": "..."}
      {"type": "result", "data":    {...}}
      {"type": "error",  "message": "..."}
    """

    def _emit(obj):
        return json.dumps(obj, ensure_ascii=False) + "\n"

    def generate():
        try:
            if request.local_path:
                local = Path(request.local_path)
                if not local.exists() or not local.is_dir():
                    yield _emit(
                        {
                            "type": "error",
                            "message": "Local path does not exist or is not a directory.",
                        }
                    )
                    return
                repo_path = str(local.resolve())
                yield _emit(
                    {"type": "log", "message": f"Using local directory: {repo_path}"}
                )
            elif request.repo_url:
                yield _emit({"type": "log", "message": "Cloning repository..."})
                repo_path = clone_repository(request.repo_url)
                yield _emit({"type": "log", "message": "Repository cloned."})
            else:
                yield _emit(
                    {
                        "type": "error",
                        "message": "Please provide a GitHub URL or a local directory path.",
                    }
                )
                return

            # ── Collect all supported source files ──────────
            yield _emit(
                {
                    "type": "log",
                    "message": "Scanning for source files across all supported languages...",
                }
            )

            supported_exts = get_all_supported_extensions()
            source_files = []

            for root, dirs, filenames in os.walk(repo_path):
                # Skip hidden/non-source dirs
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d
                    not in {
                        "__pycache__",
                        "node_modules",
                        ".git",
                        "venv",
                        ".venv",
                        "target",
                        "build",
                        "dist",
                        "bin",
                        "obj",
                        "vendor",
                        "pkg",
                    }
                ]
                for fname in filenames:
                    fpath = Path(root) / fname
                    if fpath.suffix.lower() in supported_exts:
                        source_files.append(str(fpath))

            # Group files by language
            files_by_lang = {}
            for fpath in source_files:
                lang = detect_language(fpath)
                if lang:
                    if lang not in files_by_lang:
                        files_by_lang[lang] = []
                    files_by_lang[lang].append(fpath)

            lang_summary = ", ".join(
                f"{lang}: {len(files)}" for lang, files in files_by_lang.items()
            )
            yield _emit(
                {
                    "type": "log",
                    "message": f"Found {len(source_files)} source files ({lang_summary})",
                }
            )

            if not source_files:
                yield _emit(
                    {
                        "type": "log",
                        "message": "No supported source files found in repository.",
                    }
                )
                yield _emit(
                    {
                        "type": "result",
                        "data": {
                            "message": "No supported source files found",
                            "repo_path": repo_path,
                        },
                    }
                )
                return

            # ── For Python files: use flake8 first (fast) ───
            python_violations = []
            has_python = "python" in files_by_lang

            if has_python:
                yield _emit(
                    {"type": "log", "message": "Running flake8 on Python files..."}
                )
                python_violations = run_flake8(repo_path)
                yield _emit(
                    {
                        "type": "log",
                        "message": f"Flake8 found {len(python_violations)} Python violations.",
                    }
                )

            # ── For non-Python files: use AI agent per file ─
            non_python_files = []
            for lang, files in files_by_lang.items():
                if lang != "python":
                    for fpath in files:
                        non_python_files.append((fpath, lang))

            yield _emit(
                {
                    "type": "log",
                    "message": f"Analyzing {len(non_python_files)} non-Python files with AI agent...",
                }
            )

            # ── Process Python violations (flake8 + AI fix) ─
            snippet_cache = {}
            tasks = []

            for idx, violation in enumerate(python_violations):
                snippet, snippet_start_line = extract_snippet(
                    violation["file_path"],
                    violation["line_number"],
                )
                if not snippet.strip():
                    continue
                tasks.append((idx, violation, snippet, snippet_start_line))

            yield _emit(
                {
                    "type": "log",
                    "message": f"Generating AI fixes for {len(tasks)} Python violations...",
                }
            )

            MAX_WORKERS = 8
            completed_count = 0

            def _ai_task(snippet, violation, cache_key):
                if cache_key in snippet_cache:
                    return snippet_cache[cache_key]
                result = generate_fix(
                    snippet,
                    violation["message"],
                    rule_code=violation.get("rule_code", ""),
                    rule_standard=violation.get("rule_standard", ""),
                )
                snippet_cache[cache_key] = result
                return result

            ai_results = {}

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                future_map = {}
                for idx, violation, snippet, _ in tasks:
                    cache_key = (snippet, violation.get("rule_code", ""))
                    if cache_key in snippet_cache:
                        ai_results[idx] = snippet_cache[cache_key]
                        continue
                    future = pool.submit(_ai_task, snippet, violation, cache_key)
                    future_map[future] = idx

                total_futures = len(future_map)
                for future in as_completed(future_map):
                    ai_results[future_map[future]] = future.result()
                    completed_count += 1
                    if completed_count % 5 == 0 or completed_count == total_futures:
                        yield _emit(
                            {
                                "type": "log",
                                "message": f"Python AI fixes: {completed_count}/{total_futures}",
                            }
                        )

            # ── Assemble Python results ─────────────────────
            results = []
            for idx, violation, snippet, snippet_start_line in tasks:
                ai_result = ai_results.get(idx)
                if ai_result is None:
                    continue

                diff = generate_diff(snippet, ai_result["fixed_code"])

                rel_path = violation["file_path"]
                if repo_path and rel_path.startswith(repo_path):
                    rel_path = rel_path[len(repo_path) :].lstrip("/")

                results.append(
                    {
                        "file": violation["file_path"],
                        "file_relative": rel_path,
                        "line": violation["line_number"],
                        "column": violation["column"],
                        "snippet_start_line": snippet_start_line,
                        "rule_code": violation.get("rule_code", ""),
                        "rule_standard": violation.get("rule_standard", ""),
                        "rule_description": violation.get("rule_description", ""),
                        "violation": violation["message"],
                        "explanation": ai_result["explanation"],
                        "original_code": snippet,
                        "suggested_code": ai_result["fixed_code"],
                        "diff": diff,
                        "language": "python",
                        "severity": "warning",
                    }
                )

            # ── Process non-Python files with AI agent ──────
            agent_completed = 0
            total_agent = len(non_python_files)

            for fpath, lang in non_python_files:
                try:
                    with open(fpath, "r", errors="replace") as f:
                        file_code = f.read()

                    if not file_code.strip():
                        agent_completed += 1
                        continue

                    # Limit file size for AI (avoid token overflow)
                    if len(file_code) > 15000:
                        file_code = file_code[:15000]

                    analysis = analyze_code(file_code, lang)

                    rel_path = fpath
                    if repo_path and rel_path.startswith(repo_path):
                        rel_path = rel_path[len(repo_path) :].lstrip("/")

                    for v in analysis.get("violations", []):
                        results.append(
                            {
                                "file": fpath,
                                "file_relative": rel_path,
                                "line": v.get("line", 0),
                                "column": v.get("column", 1),
                                "snippet_start_line": max(1, v.get("line", 1) - 5),
                                "rule_code": v.get("rule_code", ""),
                                "rule_standard": v.get("rule_standard", ""),
                                "rule_description": v.get("rule_description", ""),
                                "violation": v.get("message", ""),
                                "explanation": v.get("explanation", ""),
                                "original_code": v.get("original_code", ""),
                                "suggested_code": v.get("suggested_code", ""),
                                "diff": v.get("diff", ""),
                                "language": lang,
                                "severity": v.get("severity", "warning"),
                            }
                        )

                except Exception as e:
                    print(f"Agent error on {fpath}: {e}")

                agent_completed += 1
                if agent_completed % 3 == 0 or agent_completed == total_agent:
                    yield _emit(
                        {
                            "type": "log",
                            "message": f"Agent analysis: {agent_completed}/{total_agent} files",
                        }
                    )

            yield _emit(
                {
                    "type": "log",
                    "message": f"Scan complete. {len(results)} total violations across all languages.",
                }
            )
            yield _emit(
                {
                    "type": "result",
                    "data": {
                        "repo_path": repo_path,
                        "total_violations": len(results),
                        "violations": results,
                        "languages_analyzed": list(files_by_lang.keys()),
                    },
                }
            )

        except Exception as e:
            print(traceback.format_exc())
            yield _emit({"type": "error", "message": str(e)})

    return StreamingResponse(generate(), media_type="text/plain")


# =========================================================
# Apply Linters & Formatters
# =========================================================


@app.post("/apply-linters")
def apply_linters(request: ApplyLintersRequest):
    """
    Run black (formatter), isort (import sorter), and autopep8 (PEP 8 fixer)
    on the cloned repository, then re-scan to show remaining violations.
    """
    try:
        repo_path = request.repo_path

        if not Path(repo_path).exists():
            raise ValueError("Repository path does not exist.")

        tools_run = []

        # 1. Run autoflake (remove unused imports & variables)
        try:
            subprocess.run(
                [
                    "autoflake",
                    "--in-place",
                    "--recursive",
                    "--remove-all-unused-imports",
                    "--remove-unused-variables",
                    "--ignore-init-module-imports",
                    repo_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            tools_run.append("autoflake")
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"autoflake warning: {e}")

        # 2. Run isort (sort imports)
        try:
            subprocess.run(
                ["isort", "--profile", "black", repo_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
            tools_run.append("isort")
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"isort warning: {e}")

        # 3. Run autopep8 (fix PEP 8 issues)
        try:
            subprocess.run(
                ["autopep8", "--in-place", "--recursive", "--aggressive", repo_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
            tools_run.append("autopep8")
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"autopep8 warning: {e}")

        # 4. Run black (code formatter)
        try:
            subprocess.run(
                ["black", "--quiet", repo_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
            tools_run.append("black")
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"black warning: {e}")

        # 5. Re-scan to find remaining violations
        remaining = run_flake8(repo_path)

        remaining_results = []
        for violation in remaining:
            rel_path = violation["file_path"]
            if repo_path and rel_path.startswith(repo_path):
                rel_path = rel_path[len(repo_path) :].lstrip("/")

            remaining_results.append(
                {
                    "file_relative": rel_path,
                    "line": violation["line_number"],
                    "column": violation["column"],
                    "rule_code": violation.get("rule_code", ""),
                    "rule_standard": violation.get("rule_standard", ""),
                    "rule_description": violation.get("rule_description", ""),
                    "violation": violation["message"],
                }
            )

        return {
            "tools_applied": tools_run,
            "remaining_violations": len(remaining_results),
            "violations": remaining_results,
        }

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# Download Corrected Files
# =========================================================


@app.get("/download-fixed")
def download_fixed(repo_path: str):
    """
    Zip the (already linter-corrected) repository and return
    it as a downloadable .zip file.
    """
    try:
        repo = Path(repo_path)
        if not repo.exists() or not repo.is_dir():
            raise ValueError("Repository path does not exist.")

        # Create a zip archive in a temp location
        zip_dir = tempfile.mkdtemp()
        repo_name = repo.name or "corrected-repo"
        zip_path = Path(zip_dir) / repo_name

        archive_path = shutil.make_archive(
            str(zip_path), "zip", root_dir=str(repo), base_dir="."
        )

        return FileResponse(
            path=archive_path,
            media_type="application/zip",
            filename=f"{repo_name}-fixed.zip",
        )

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# Get Corrected File Contents (for copy from browser)
# =========================================================


@app.get("/corrected-files")
def get_corrected_files(repo_path: str):
    """
    Walk the repo directory and return the contents of all
    supported source files so the frontend can display them for copying.
    """
    try:
        repo = Path(repo_path)
        if not repo.exists() or not repo.is_dir():
            raise ValueError("Repository path does not exist.")

        files = {}
        supported_exts = get_all_supported_extensions()

        for root, dirs, filenames in os.walk(repo):
            # Skip hidden dirs and common non-source dirs
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in {
                    "__pycache__",
                    "node_modules",
                    ".git",
                    "venv",
                    ".venv",
                    "target",
                    "build",
                    "dist",
                    "bin",
                    "obj",
                    "vendor",
                }
            ]
            for fname in sorted(filenames):
                fpath = Path(root) / fname
                if fpath.suffix.lower() not in supported_exts:
                    continue
                rel = str(fpath.relative_to(repo))
                try:
                    files[rel] = fpath.read_text(errors="replace")
                except Exception:
                    files[rel] = "# Could not read file"

        return {"files": files}

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
