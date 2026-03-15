# app/services/agent_service.py
"""
AI Agent Service — Autonomous code analysis for multiple languages.

Unlike the pipeline approach (flake8 → parse → AI fix), this agent uses
the LLM itself to IDENTIFY violations, making it language-agnostic.
It works for Python, C++, Java, JavaScript, TypeScript, Go, and Rust.
"""

from __future__ import annotations

import json
import traceback

from app.llm.agent_prompts import (
    analyze_prompt,
    fix_all_prompt,
    get_language_context,
    get_language_info,
    get_supported_languages,
)
from app.llm.llm_provider import get_llm
from app.services.ai_service import clean_markdown
from app.services.diff_service import generate_diff


# ─────────────────────────────────────────────────────────────
# Language Detection
# ─────────────────────────────────────────────────────────────

EXTENSION_MAP = {
    ".py": "python",
    ".pyw": "python",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".go": "go",
    ".rs": "rust",
}


def detect_language(filename: str) -> str | None:
    """Detect language from file extension."""
    for ext, lang in EXTENSION_MAP.items():
        if filename.lower().endswith(ext):
            return lang
    return None


def get_all_supported_extensions() -> set:
    """Return all supported file extensions."""
    return set(EXTENSION_MAP.keys())


# ─────────────────────────────────────────────────────────────
# Core Agent — Analyze Code
# ─────────────────────────────────────────────────────────────


def _extract_json(text: str) -> dict:
    """
    Robustly extract JSON from an LLM response that may contain
    markdown fencing or extra text around the JSON.
    """
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Remove markdown fencing
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # drop ```json line
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Try to find JSON object in the text
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    # Last resort — return empty structure
    return {"violations": [], "summary": {"total_violations": 0}}


def analyze_code(code: str, language: str) -> dict:
    """
    Use the AI agent to autonomously analyze code for violations.

    Args:
        code: The source code to analyze
        language: The programming language (python, cpp, java, etc.)

    Returns:
        dict with 'violations' list and 'summary'
    """
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
        lang_context = get_language_context(language)

        chain = analyze_prompt | llm

        response = chain.invoke(
            {
                "language": language,
                "language_context": lang_context,
                "code": code,
            }
        )

        content = response.content.strip()
        result = _extract_json(content)

        # Ensure all violations have required fields and generate diffs
        violations = result.get("violations", [])
        processed = []

        for v in violations:
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

        return {
            "violations": processed,
            "summary": summary,
        }

    except Exception as e:
        traceback.print_exc()
        return {
            "violations": [],
            "summary": {
                "total_violations": 0,
                "error": f"Analysis failed: {str(e)}",
            },
        }


# ─────────────────────────────────────────────────────────────
# Agent — Fix All Violations
# ─────────────────────────────────────────────────────────────


def fix_all_violations(code: str, language: str, violations: list) -> dict:
    """
    Use the AI agent to fix ALL violations in the code at once.

    Returns:
        dict with 'explanation' and 'fixed_code'
    """
    language = language.lower()

    try:
        llm = get_llm()
        lang_context = get_language_context(language)

        # Build violations summary for the prompt
        violations_summary = "\n".join(
            f"  - Line {v.get('line', '?')}: [{v.get('rule_code', '')}] {v.get('message', '')}"
            for v in violations
        )

        chain = fix_all_prompt | llm

        response = chain.invoke(
            {
                "language": language,
                "language_context": lang_context,
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

        explanation_part = content.split("Fixed Code:")[0]
        fixed_part = content.split("Fixed Code:")[1]

        explanation = explanation_part.replace("Explanation:", "").strip()
        fixed_code = clean_markdown(fixed_part)

        if not fixed_code:
            fixed_code = code

        return {
            "explanation": explanation,
            "fixed_code": fixed_code,
        }

    except Exception as e:
        traceback.print_exc()
        return {
            "explanation": f"Fix generation failed: {str(e)}",
            "fixed_code": code,
        }
