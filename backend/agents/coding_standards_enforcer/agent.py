"""
Core agent logic — analyzes code, generates fixes, and orchestrates a
streaming repo scan.

All LLM access flows through `core.services.llm_service.get_llm()`.
"""
from __future__ import annotations

import difflib
import json
import logging
import os
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from core.services.llm_service import get_llm
from agents.coding_standards_enforcer.parsers import (
    detect_language,
    get_all_supported_extensions,
)
from agents.coding_standards_enforcer.parsers.language_detector import SKIP_DIRS
from agents.coding_standards_enforcer.linters.flake8_runner import (
    extract_snippet,
    run_flake8,
)
from agents.coding_standards_enforcer.linters.apply_linters import (
    format_python_in_memory,
    run_python_formatters,
)
from agents.coding_standards_enforcer.repo.git_client import clone_repository
from agents.coding_standards_enforcer.prompts import (
    analyze_prompt,
    fix_all_prompt,
    fix_prompt,
    get_language_context,
    get_supported_languages,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────


def generate_diff(original: str, modified: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(), modified.splitlines(), lineterm=""
    )
    return "\n".join(diff)


def clean_markdown(code: str) -> str:
    """Strip ``` fences from an LLM response."""
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)
    if code.startswith("```"):
        parts = code.split("```")
        if len(parts) >= 2:
            code = parts[1]
    return code.strip()


def _extract_json(text: str) -> dict:
    """Robust JSON extraction tolerant to markdown fencing and surrounding text."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    return {"violations": [], "summary": {"total_violations": 0}}


# ─────────────────────────────────────────────────────────────
# Live single-file analysis (LLM agent)
# ─────────────────────────────────────────────────────────────


def analyze_code(code: str, language: str) -> dict:
    """Use the LLM to autonomously identify violations in a code blob."""
    language = language.lower()
    if language not in get_supported_languages():
        return {
            "violations": [],
            "summary": {
                "total_violations": 0,
                "error": f"Unsupported language: {language}",
            },
        }

    try:
        llm = get_llm()
        chain = analyze_prompt | llm
        response = chain.invoke(
            {
                "language": language,
                "language_context": get_language_context(language),
                "code": code,
            }
        )
        result = _extract_json(response.content.strip())

        processed: List[dict] = []
        for v in result.get("violations", []):
            original = v.get("original_code", "")
            suggested = v.get("suggested_code", original)
            diff = generate_diff(original, suggested) if original else ""
            processed.append(
                {
                    "line": v.get("line", 0),
                    "column": v.get("column", 1),
                    "rule_code": v.get("rule_code", "STYLE"),
                    "rule_standard": v.get("rule_standard", "Coding Standard"),
                    "rule_description": v.get("rule_description", ""),
                    "message": v.get("message", "Coding standard violation"),
                    "severity": v.get("severity", "warning"),
                    "original_code": original,
                    "suggested_code": suggested,
                    "explanation": v.get("explanation", ""),
                    "diff": diff,
                }
            )

        summary = result.get("summary", {})
        summary["total_violations"] = len(processed)
        return {"violations": processed, "summary": summary}

    except Exception as e:
        traceback.print_exc()
        return {
            "violations": [],
            "summary": {
                "total_violations": 0,
                "error": f"Analysis failed: {e}",
            },
        }


# ─────────────────────────────────────────────────────────────
# Fix-all (LLM agent)
# ─────────────────────────────────────────────────────────────


def fix_all_violations(code: str, language: str, violations: List[dict]) -> dict:
    """Ask the LLM to rewrite the whole code blob with every violation fixed."""
    language = language.lower()

    try:
        llm = get_llm()
        violations_summary = "\n".join(
            f"  - Line {v.get('line', '?')}: [{v.get('rule_code', '')}] {v.get('message', '')}"
            for v in violations
        )

        chain = fix_all_prompt | llm
        response = chain.invoke(
            {
                "language": language,
                "language_context": get_language_context(language),
                "code": code,
                "violations_summary": violations_summary,
            }
        )

        content = response.content.strip()
        if "Fixed Code:" not in content:
            return {
                "explanation": "AI could not generate fixes.",
                "fixed_code": code,
            }

        explanation_part, fixed_part = content.split("Fixed Code:", 1)
        explanation = explanation_part.replace("Explanation:", "").strip()
        fixed_code = clean_markdown(fixed_part) or code

        return {"explanation": explanation, "fixed_code": fixed_code}

    except Exception as e:
        traceback.print_exc()
        return {
            "explanation": f"Fix generation failed: {e}",
            "fixed_code": code,
        }


# ─────────────────────────────────────────────────────────────
# Single-violation fix (used by the deterministic Python pipeline)
# ─────────────────────────────────────────────────────────────


def generate_fix(
    code_snippet: str,
    violation_message: str,
    rule_code: str = "",
    rule_standard: str = "",
) -> dict:
    try:
        llm = get_llm()
        chain = fix_prompt | llm
        response = chain.invoke(
            {
                "violation": violation_message,
                "rule_code": rule_code,
                "rule_standard": rule_standard,
                "code": code_snippet,
            }
        )
        content = response.content.strip()
        if "Fixed Code:" not in content:
            return {
                "explanation": "AI response malformed.",
                "fixed_code": code_snippet,
            }

        explanation_part, fixed_part = content.split("Fixed Code:", 1)
        explanation = explanation_part.replace("Explanation:", "").strip()
        fixed_code = clean_markdown(fixed_part) or code_snippet

        return {"explanation": explanation, "fixed_code": fixed_code}

    except Exception as e:
        return {
            "explanation": f"AI failed: {e}",
            "fixed_code": code_snippet,
        }


# ─────────────────────────────────────────────────────────────
# Repo file walking
# ─────────────────────────────────────────────────────────────


def collect_repo_files(repo_path: str) -> Tuple[List[str], Dict[str, List[str]]]:
    """Walk a repo and return (all_supported_files, files_grouped_by_language)."""
    supported_exts = get_all_supported_extensions()
    source_files: List[str] = []

    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [
            d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS
        ]
        for fname in filenames:
            fpath = Path(root) / fname
            if fpath.suffix.lower() in supported_exts:
                source_files.append(str(fpath))

    files_by_lang: Dict[str, List[str]] = {}
    for fpath in source_files:
        lang = detect_language(fpath)
        if lang:
            files_by_lang.setdefault(lang, []).append(fpath)

    return source_files, files_by_lang


def load_repo_files_for_editor(
    repo_path: str, max_size_bytes: int = 100_000
) -> Dict[str, dict]:
    """Read every supported source file under repo_path and return path→file dict."""
    supported_exts = get_all_supported_extensions()
    files: Dict[str, dict] = {}
    repo = Path(repo_path)

    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [
            d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS
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
                if len(content) > max_size_bytes:
                    content = (
                        content[:max_size_bytes]
                        + "\n\n// ... (file truncated — too large for editor)"
                    )
            except Exception:
                content = "// Could not read file"

            files[rel] = {
                "content": content,
                "language": lang or "plaintext",
                "size_bytes": fpath.stat().st_size if fpath.exists() else 0,
            }

    return files


# ─────────────────────────────────────────────────────────────
# Streaming repo scan
# ─────────────────────────────────────────────────────────────


def _emit(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False) + "\n"


def stream_scan(
    repo_url: str = "",
    local_path: str = "",
    max_workers: int = 8,
    max_llm_file_size: int = 15_000,
) -> Iterator[str]:
    """Yield NDJSON frames describing the scan progress and final result."""
    try:
        if local_path:
            local = Path(local_path)
            if not local.exists() or not local.is_dir():
                yield _emit(
                    {
                        "type": "error",
                        "message": "Local path does not exist or is not a directory.",
                    }
                )
                return
            repo_path = str(local.resolve())
            yield _emit({"type": "log", "message": f"Using local directory: {repo_path}"})
        elif repo_url:
            yield _emit({"type": "log", "message": "Cloning repository..."})
            repo_path = clone_repository(repo_url)
            yield _emit({"type": "log", "message": "Repository cloned."})
        else:
            yield _emit(
                {
                    "type": "error",
                    "message": "Please provide a GitHub URL or a local directory path.",
                }
            )
            return

        yield _emit(
            {
                "type": "log",
                "message": "Scanning for source files across all supported languages...",
            }
        )
        source_files, files_by_lang = collect_repo_files(repo_path)

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

        # ── Python pipeline: flake8 + AI fixes (parallel) ─────────────
        python_violations: List[dict] = []
        if "python" in files_by_lang:
            yield _emit({"type": "log", "message": "Running flake8 on Python files..."})
            python_violations = run_flake8(repo_path)
            yield _emit(
                {
                    "type": "log",
                    "message": f"Flake8 found {len(python_violations)} Python violations.",
                }
            )

        non_python_files: List[Tuple[str, str]] = []
        for lang, files in files_by_lang.items():
            if lang != "python":
                non_python_files.extend((f, lang) for f in files)

        yield _emit(
            {
                "type": "log",
                "message": f"Analyzing {len(non_python_files)} non-Python files with AI agent...",
            }
        )

        snippet_cache: Dict[Tuple[str, str], dict] = {}
        tasks: List[Tuple[int, dict, str, int]] = []

        for idx, violation in enumerate(python_violations):
            snippet, snippet_start_line = extract_snippet(
                violation["file_path"], violation["line_number"]
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

        def _ai_task(snippet: str, violation: dict, cache_key: tuple) -> dict:
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

        ai_results: Dict[int, dict] = {}
        completed_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
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
                            "message": (
                                f"Python AI fixes: {completed_count}/{total_futures}"
                            ),
                        }
                    )

        # ── Assemble Python results ──────────────────────────────────
        results: List[dict] = []
        for idx, violation, snippet, snippet_start_line in tasks:
            ai_result = ai_results.get(idx)
            if ai_result is None:
                continue

            diff = generate_diff(snippet, ai_result["fixed_code"])
            rel_path = violation["file_path"]
            if repo_path and rel_path.startswith(repo_path):
                rel_path = rel_path[len(repo_path):].lstrip("/")

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

        # ── Non-Python files: per-file LLM analysis ───────────────────
        agent_completed = 0
        total_agent = len(non_python_files)

        for fpath, lang in non_python_files:
            try:
                with open(fpath, "r", errors="replace") as f:
                    file_code = f.read()

                if not file_code.strip():
                    agent_completed += 1
                    continue

                if len(file_code) > max_llm_file_size:
                    file_code = file_code[:max_llm_file_size]

                analysis = analyze_code(file_code, lang)

                rel_path = fpath
                if repo_path and rel_path.startswith(repo_path):
                    rel_path = rel_path[len(repo_path):].lstrip("/")

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
                logger.warning("Agent error on %s: %s", fpath, e)

            agent_completed += 1
            if agent_completed % 3 == 0 or agent_completed == total_agent:
                yield _emit(
                    {
                        "type": "log",
                        "message": (
                            f"Agent analysis: {agent_completed}/{total_agent} files"
                        ),
                    }
                )

        yield _emit(
            {
                "type": "log",
                "message": (
                    f"Scan complete. {len(results)} total violations across all languages."
                ),
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
        traceback.print_exc()
        yield _emit({"type": "error", "message": str(e)})


# ─────────────────────────────────────────────────────────────
# Apply linters helper (Python only)
# ─────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────
# Iterative final-fix ("polish")
# ─────────────────────────────────────────────────────────────


def polish_code(
    code: str,
    language: str,
    max_passes: int = 5,
) -> dict:
    """
    Produce a definitively cleaned-up version of ``code``.

    Strategy:
      1. (Python only) Run autoflake/isort/autopep8/black in-memory first —
         this kills the easy mechanical violations the LLM keeps missing.
      2. Analyse → if violations remain, ask the LLM to fix → re-run
         formatters (Python only) → re-analyse. Repeat up to ``max_passes``
         times or until convergence.

    Returns the final code, the violation list at exit, and metadata about
    what ran.
    """
    language = language.lower()
    is_python = language == "python"

    history: List[dict] = []
    current = code

    # Step 0 — let the deterministic Python tools take a swing first.
    if is_python:
        current, formatters = format_python_in_memory(current)
        history.append({"pass": 0, "stage": "formatters", "tools": formatters})

    last_violations: List[dict] = []

    for i in range(1, max_passes + 1):
        analysis = analyze_code(current, language)
        last_violations = analysis.get("violations", []) or []
        history.append(
            {
                "pass": i,
                "stage": "analyze",
                "violations": len(last_violations),
            }
        )
        if not last_violations:
            break

        result = fix_all_violations(current, language, last_violations)
        candidate = result.get("fixed_code", current)
        if not candidate.strip() or candidate == current:
            # LLM gave up or returned the same code — stop, no progress.
            history.append(
                {"pass": i, "stage": "llm_fix", "noop": True}
            )
            break

        current = candidate
        history.append({"pass": i, "stage": "llm_fix", "noop": False})

        if is_python:
            current, formatters = format_python_in_memory(current)
            history.append(
                {"pass": i, "stage": "formatters", "tools": formatters}
            )

    # Final analysis — what remains after the last action.
    final_analysis = analyze_code(current, language)
    final_violations = final_analysis.get("violations", []) or []

    return {
        "fixed_code": current,
        "diff": generate_diff(code, current),
        "passes_used": min(i, max_passes) if last_violations or i > 0 else 0,
        "remaining_violations": final_violations,
        "history": history,
    }


def apply_linters_to_repo(repo_path: str) -> dict:
    """Run formatters then re-scan with flake8."""
    if not Path(repo_path).exists():
        raise ValueError("Repository path does not exist.")

    tools_run = run_python_formatters(repo_path)
    remaining = run_flake8(repo_path)

    remaining_results = []
    for violation in remaining:
        rel_path = violation["file_path"]
        if repo_path and rel_path.startswith(repo_path):
            rel_path = rel_path[len(repo_path):].lstrip("/")
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


# ─────────────────────────────────────────────────────────────
# Apply fix helper (legacy)
# ─────────────────────────────────────────────────────────────


def apply_fix(file_path: str, original_code: str, suggested_code: str) -> bool:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{file_path} not found")
    content = path.read_text()
    if original_code not in content:
        return False
    path.write_text(content.replace(original_code, suggested_code, 1))
    return True
