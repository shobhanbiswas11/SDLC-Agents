# repo_summarizer/section_detector.py
"""
Smart Section Detection

Reads an existing README.md (if any) and extracts which top-level and
second-level sections (headings) are already present. The pipeline uses
this to tell the LLM which sections are fresh, which are stale, and
which are missing — reducing unnecessary rewrites.

Usage:
    from generators.section_detector import detect_existing_sections, build_section_diff, fetch_existing_readme
    headings = detect_existing_sections(readme_content)
    diff = build_section_diff(headings, requested_sections)
"""

import re
import os
import requests
from typing import Optional


# ── Canonical section name map ────────────────────────────────────────────────
# Normalise common heading aliases so "Getting Started" == "Installation", etc.
_ALIASES: dict[str, str] = {
    "getting started": "Installation",
    "installation": "Installation",
    "setup": "Installation",
    "quickstart": "Installation",
    "quick start": "Installation",
    "usage": "Usage Guide",
    "usage guide": "Usage Guide",
    "how to use": "Usage Guide",
    "features": "Features",
    "feature list": "Features",
    "tech stack": "Tech Stack",
    "technology stack": "Tech Stack",
    "technologies": "Tech Stack",
    "built with": "Tech Stack",
    "api reference": "API Reference",
    "api": "API Reference",
    "endpoints": "API Reference",
    "environment variables": "Environment Variables",
    "env vars": "Environment Variables",
    "configuration": "Environment Variables",
    "contributing": "Contributing",
    "contribution": "Contributing",
    "how to contribute": "Contributing",
    "license": "License",
    "architecture": "Architecture",
    "system design": "Architecture",
    "overview": "Architecture",
}


def _normalise(heading: str) -> str:
    """Return canonical section name or the original title-cased heading."""
    key = heading.strip().lower()
    return _ALIASES.get(key, heading.strip().title())


# ── Core extraction ───────────────────────────────────────────────────────────

def detect_existing_sections(readme_content: str) -> list[str]:
    """
    Parse a README string and return a list of canonical section names.

    Captures both # H1 and ## H2 headings. Ignores deeper headings (###, ####)
    since they are subsections, not top-level sections.

    Args:
        readme_content: Raw markdown string.

    Returns:
        List of canonical section name strings, in document order.
    """
    if not readme_content or not readme_content.strip():
        return []

    headings: list[str] = []
    # Match `# Title` or `## Title` at the start of a line
    pattern = re.compile(r'^#{1,2}\s+(.+)', re.MULTILINE)
    for m in pattern.finditer(readme_content):
        raw = m.group(1).strip()
        # Strip inline code, bold, italic, and emoji
        raw = re.sub(r'[`*_~]', '', raw)
        raw = re.sub(r':\w+:', '', raw)  # :emoji:
        raw = raw.strip()
        if raw:
            canonical = _normalise(raw)
            if canonical not in headings:
                headings.append(canonical)

    return headings


# ── Section diff ─────────────────────────────────────────────────────────────

def build_section_diff(
    existing: list[str],
    requested: list[str] | None = None
) -> dict[str, list[str]]:
    """
    Compare existing README sections against what is requested.

    Args:
        existing:  Sections found in the current README.
        requested: Sections the user asked for (from the API request).
                   If None or empty, uses the default 9 standard sections.

    Returns:
        {
            "present": [...],   # sections already in README
            "missing": [...],   # sections not yet in README
            "extra":   [...],   # sections in README not in requested list
        }
    """
    _DEFAULT_SECTIONS = [
        "Features",
        "Tech Stack",
        "Installation",
        "Usage Guide",
        "Environment Variables",
        "API Reference",
        "Contributing",
        "License",
        "Architecture",
    ]

    target = [_normalise(s) for s in (requested or _DEFAULT_SECTIONS)]
    existing_set = set(existing)

    present = [s for s in target if s in existing_set]
    missing = [s for s in target if s not in existing_set]
    extra   = [s for s in existing if s not in set(target)]

    return {"present": present, "missing": missing, "extra": extra}


def format_section_diff_prompt(diff: dict[str, list[str]]) -> str:
    """
    Format the section diff into a prompt block for the LLM.

    Returns a string like:

        ====== SMART SECTION DETECTION ======
        Already present in README: [Installation, Tech Stack, Usage Guide]
        Missing / To Generate    : [API Reference, Contributing, Architecture]
        Extra (keep if relevant) : [Roadmap]

        INSTRUCTIONS:
        - For sections listed as "Already present": keep them if the code still
          matches. Update only what has clearly changed.
        - For "Missing" sections: generate them fresh from the code context.
        - Do NOT remove "Extra" sections unless the code contradicts them.
        ======================================
    """
    if not diff:
        return ""

    present_str = ", ".join(diff.get("present", [])) or "None"
    missing_str = ", ".join(diff.get("missing", [])) or "None"
    extra_str   = ", ".join(diff.get("extra",   [])) or "None"

    return f"""
====== SMART SECTION DETECTION ======
Already present in README : [{present_str}]
Missing / To Generate     : [{missing_str}]
Extra sections (keep if relevant) : [{extra_str}]

INSTRUCTIONS:
- For sections listed as "Already present": keep them if the code still matches. Update only what has clearly changed.
- For "Missing" sections: generate them fresh from the code context.
- Do NOT remove "Extra" sections unless the code clearly contradicts them.
======================================"""


# ── README fetchers ───────────────────────────────────────────────────────────

def fetch_existing_readme_local(local_path: str) -> Optional[str]:
    """
    Read the existing README.md from a local directory.
    Returns the content string, or None if not found.
    """
    for name in ("README.md", "readme.md", "Readme.md", "README.MD", "README.rst"):
        candidate = os.path.join(local_path, name)
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            continue
        except Exception:
            continue
    return None


def fetch_existing_readme_github(
    repo_name: str,
    token: str,
    branch: str = "main",
) -> Optional[str]:
    """
    Fetch the existing README.md from a GitHub repository via the API.
    Returns the raw content string, or None if it doesn't exist or fails.
    """
    if not repo_name or not token:
        return None
    try:
        owner, repo = repo_name.split("/", 1)
    except ValueError:
        return None

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/README.md"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.raw",
    }
    try:
        resp = requests.get(url, headers=headers, params={"ref": branch}, timeout=15)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None
