"""Prompt templates and standards reference data."""
from .analyze import (
    LANGUAGE_STANDARDS,
    analyze_prompt,
    get_language_context,
    get_language_info,
    get_supported_languages,
)
from .fix import fix_all_prompt, fix_prompt
from .coding_standards import CODING_STANDARDS, get_rule_info

__all__ = [
    "LANGUAGE_STANDARDS",
    "analyze_prompt",
    "fix_all_prompt",
    "fix_prompt",
    "CODING_STANDARDS",
    "get_rule_info",
    "get_language_context",
    "get_language_info",
    "get_supported_languages",
]
