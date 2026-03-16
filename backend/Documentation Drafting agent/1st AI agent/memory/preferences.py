# memory/preferences.py
"""
Per-repo user preferences for README generation.

Stores customisation options (sections to include/exclude, tone, extra
instructions) in a JSON file under memory/{owner_repo}_prefs.json.
"""

import json
import os
from typing import Dict, Any, Optional, List


_MEMORY_DIR = "memory"


# Default preferences (used when no prefs file exists)
_DEFAULTS: Dict[str, Any] = {
    "include_sections": [],
    "exclude_sections": [],
    "tone": "professional",
    "extra_instructions": "",
    "custom_badges": [],
    "auto_generate_on_push": True,
}


def _prefs_path(repo_name: str) -> str:
    return os.path.join(_MEMORY_DIR, f"{repo_name.replace('/', '_')}_prefs.json")


def load_preferences(repo_name: str) -> Dict[str, Any]:
    """
    Load preferences for a repo. Returns defaults if none saved.

    Keys:
      - include_sections: list[str]  — additional sections to add (e.g. "Docker Setup")
      - exclude_sections: list[str]  — sections to omit (e.g. "License")
      - tone: str                    — "professional", "concise", "detailed", "casual"
      - extra_instructions: str      — freeform text injected into prompt
      - custom_badges: list[str]     — badge types to add (e.g. "build", "coverage")
    """
    path = _prefs_path(repo_name)
    if not os.path.exists(path):
        return dict(_DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge with defaults so new keys are always present
        merged = dict(_DEFAULTS)
        merged.update(data)
        return merged
    except Exception:
        return dict(_DEFAULTS)


def save_preferences(repo_name: str, prefs: Dict[str, Any]) -> str:
    """
    Save preferences to disk. Returns the file path.

    Only known keys are persisted; unknown keys are silently dropped.
    """
    os.makedirs(_MEMORY_DIR, exist_ok=True)
    path = _prefs_path(repo_name)

    # Only keep known keys
    clean = {}
    for key in _DEFAULTS:
        if key in prefs:
            clean[key] = prefs[key]
        else:
            clean[key] = _DEFAULTS[key]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2)
    return path


def format_preferences_prompt(prefs: Dict[str, Any]) -> str:
    """
    Convert preferences into an instruction block for the LLM prompt.

    Returns an empty string if all preferences are default (nothing to add).
    """
    lines: List[str] = []

    include = prefs.get("include_sections", [])
    exclude = prefs.get("exclude_sections", [])
    tone = prefs.get("tone", "professional")
    extra = prefs.get("extra_instructions", "")
    badges = prefs.get("custom_badges", [])

    # Tone
    if tone and tone != "professional":
        tone_map = {
            "concise": "Keep the README concise and to-the-point. Avoid verbose explanations.",
            "detailed": "Make the README very detailed and thorough. Explain every section comprehensively.",
            "casual": "Write in a casual, friendly tone. Use emojis where appropriate.",
        }
        if tone in tone_map:
            lines.append(f"TONE: {tone_map[tone]}")
        else:
            lines.append(f"TONE: Write in a {tone} tone.")

    # Include extra sections
    if include:
        sections = ", ".join(include)
        lines.append(f"ADDITIONAL SECTIONS: You MUST include these extra sections: {sections}")

    # Exclude sections
    if exclude:
        sections = ", ".join(exclude)
        lines.append(f"EXCLUDED SECTIONS: Do NOT include these sections: {sections}")

    # Badges
    if badges:
        badge_list = ", ".join(badges)
        lines.append(f"BADGES: Add these badge types at the top of the README: {badge_list}")

    # Freeform extra instructions
    if extra and extra.strip():
        lines.append(f"CUSTOM INSTRUCTIONS: {extra.strip()}")

    if not lines:
        return ""

    return "User Preferences:\n" + "\n".join(f"- {line}" for line in lines)
