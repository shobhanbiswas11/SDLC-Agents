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

from app.services.ai_service import generate_fix
from app.services.diff_service import generate_diff
from app.services.repo_service import clone_repository
from app.services.scan_service import extract_snippet, run_flake8

app = FastAPI(title="AI Coding Standards Enforcer")


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


class ApplyLintersRequest(BaseModel):
    repo_path: str


# =========================================================
# Health Check
# =========================================================


@app.get("/")
def health():
    return {"status": "Backend running"}


# =========================================================
# Scan Repository
# =========================================================


@app.post("/scan")
def scan_repo(request: ScanRequest):
    """
    Stream scan progress as newline-delimited JSON.
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

            yield _emit({"type": "log", "message": "Running flake8 analysis..."})
            violations = run_flake8(repo_path)

            if not violations:
                yield _emit(
                    {"type": "log", "message": "No violations found — code is clean!"}
                )
                yield _emit(
                    {
                        "type": "result",
                        "data": {
                            "message": "No violations found",
                            "repo_path": repo_path,
                        },
                    }
                )
                return

            yield _emit(
                {
                    "type": "log",
                    "message": f"Found {len(violations)} violations. Extracting code snippets...",
                }
            )

            # ── Extract snippets & deduplicate ──────────────
            snippet_cache = {}
            tasks = []

            for idx, violation in enumerate(violations):
                snippet, snippet_start_line = extract_snippet(
                    violation["file_path"],
                    violation["line_number"],
                )
                if not snippet.strip():
                    continue
                tasks.append((idx, violation, snippet, snippet_start_line))

            unique_keys = set()
            for _, violation, snippet, _ in tasks:
                unique_keys.add((snippet, violation.get("rule_code", "")))

            yield _emit(
                {
                    "type": "log",
                    "message": f"Prepared {len(tasks)} snippets ({len(unique_keys)} unique). Generating AI fixes...",
                }
            )

            # ── Parallel AI calls ───────────────────────────
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
                                "message": f"AI fixes generated: {completed_count}/{total_futures}",
                            }
                        )

            # ── Assemble results ────────────────────────────
            yield _emit({"type": "log", "message": "Building violation report..."})
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
                    }
                )

            yield _emit(
                {
                    "type": "log",
                    "message": f"Scan complete. {len(results)} violations reported.",
                }
            )
            yield _emit(
                {
                    "type": "result",
                    "data": {
                        "repo_path": repo_path,
                        "total_violations": len(results),
                        "violations": results,
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
    Python files so the frontend can display them for copying.
    """
    try:
        repo = Path(repo_path)
        if not repo.exists() or not repo.is_dir():
            raise ValueError("Repository path does not exist.")

        files = {}
        EXTENSIONS = {".py", ".pyw"}

        for root, dirs, filenames in os.walk(repo):
            # Skip hidden dirs and common non-source dirs
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in {"__pycache__", "node_modules", ".git", "venv", ".venv"}
            ]
            for fname in sorted(filenames):
                fpath = Path(root) / fname
                if fpath.suffix not in EXTENSIONS:
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
