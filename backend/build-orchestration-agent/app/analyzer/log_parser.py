"""
Log Analyzer
-------------
Responsible for:
- Extracting meaningful error lines
- Classifying error types (multi-language)
- Structuring output for LLM reasoning
"""

import re
from typing import List, Dict


class LogAnalyzer:

    # ─── Error patterns grouped by language ────────────────
    ERROR_PATTERNS = [
        # ── Node.js ──
        {
            "type": "missing_dependency",
            "language": "nodejs",
            "pattern": r"Cannot find module ['\"](.+?)['\"]",
            "extract_target": True,
        },
        {
            "type": "script_missing",
            "language": "nodejs",
            "pattern": r"npm ERR! missing script: (.+)",
            "extract_target": True,
        },
        {
            "type": "npm_not_found",
            "language": "nodejs",
            "pattern": r"npm ERR! code E404",
            "extract_target": False,
        },
        {
            "type": "module_not_found_generic",
            "language": "nodejs",
            "pattern": r"Module not found:\s*(.+)",
            "extract_target": True,
        },
        {
            "type": "node_version_mismatch",
            "language": "nodejs",
            "pattern": r"Unsupported engine",
            "extract_target": False,
        },

        # ── Python ──
        {
            "type": "missing_dependency",
            "language": "python",
            "pattern": r"ModuleNotFoundError: No module named ['\"]?(\S+)['\"]?",
            "extract_target": True,
        },
        {
            "type": "missing_dependency",
            "language": "python",
            "pattern": r"ImportError: No module named ['\"]?(\S+)['\"]?",
            "extract_target": True,
        },
        {
            "type": "pip_install_error",
            "language": "python",
            "pattern": r"ERROR: Could not find a version that satisfies the requirement (\S+)",
            "extract_target": True,
        },
        {
            "type": "pip_no_matching",
            "language": "python",
            "pattern": r"ERROR: No matching distribution found for (\S+)",
            "extract_target": True,
        },
        {
            "type": "python_version_error",
            "language": "python",
            "pattern": r"requires Python (\S+)",
            "extract_target": True,
        },

        # ── Go ──
        {
            "type": "missing_dependency",
            "language": "go",
            "pattern": r"cannot find package \"(.+?)\"",
            "extract_target": True,
        },
        {
            "type": "go_build_error",
            "language": "go",
            "pattern": r"(\S+\.go:\d+:\d+:.*)",
            "extract_target": True,
        },

        # ── Java ──
        {
            "type": "missing_dependency",
            "language": "java",
            "pattern": r"package (\S+) does not exist",
            "extract_target": True,
        },
        {
            "type": "compilation_error",
            "language": "java",
            "pattern": r"COMPILATION ERROR",
            "extract_target": False,
        },

        # ── Generic ──
        {
            "type": "syntax_error",
            "language": "any",
            "pattern": r"SyntaxError:\s*(.+)",
            "extract_target": False,
        },
        {
            "type": "permission_denied",
            "language": "any",
            "pattern": r"Permission denied",
            "extract_target": False,
        },
        {
            "type": "out_of_memory",
            "language": "any",
            "pattern": r"(ENOMEM|Cannot allocate memory|OutOfMemoryError|MemoryError)",
            "extract_target": False,
        },
    ]

    ERROR_KEYWORDS = [
        "error",
        "ERR!",
        "Cannot find module",
        "SyntaxError",
        "Failed",
        "Module not found",
        "ModuleNotFoundError",
        "ImportError",
        "COMPILATION ERROR",
        "FATAL",
        "panic:",
        "Traceback",
    ]

    # --------------------------------------------------
    # Extract Relevant Error Lines
    # --------------------------------------------------
    def extract_error_lines(self, logs: str) -> List[str]:
        lines = logs.split("\n")

        error_lines = [
            line.strip()
            for line in lines
            if any(keyword.lower() in line.lower() for keyword in self.ERROR_KEYWORDS)
        ]

        # Keep last N lines for context (important for LLM)
        return error_lines[-30:]

    # --------------------------------------------------
    # Classify Error
    # --------------------------------------------------
    def classify_error(self, logs: str, project_type: str = None) -> Dict:
        """
        Classify the error. Optionally filter patterns by project_type.
        """
        # Map project_type to language filter
        type_to_lang = {
            "nodejs": "nodejs",
            "python": "python",
            "go": "go",
            "java_maven": "java",
            "java_gradle": "java",
        }

        lang_filter = type_to_lang.get(project_type) if project_type else None

        for pattern in self.ERROR_PATTERNS:
            # If we know the language, prioritize matching patterns
            pattern_lang = pattern.get("language", "any")

            if lang_filter and pattern_lang not in (lang_filter, "any"):
                continue

            match = re.search(pattern["pattern"], logs, re.IGNORECASE)

            if match:
                target = None

                if pattern.get("extract_target") and match.groups():
                    target = match.group(1)

                return {
                    "error_type": pattern["type"],
                    "language": pattern_lang,
                    "message": match.group(0),
                    "target": target,
                    "confidence": 0.95,
                }

        # If language-specific search found nothing, try all patterns
        if lang_filter:
            for pattern in self.ERROR_PATTERNS:
                match = re.search(pattern["pattern"], logs, re.IGNORECASE)

                if match:
                    target = None
                    if pattern.get("extract_target") and match.groups():
                        target = match.group(1)

                    return {
                        "error_type": pattern["type"],
                        "language": pattern.get("language", "any"),
                        "message": match.group(0),
                        "target": target,
                        "confidence": 0.8,
                    }

        return {
            "error_type": "unknown_error",
            "language": "unknown",
            "message": "Could not classify error",
            "target": None,
            "confidence": 0.3,
        }

    # --------------------------------------------------
    # Main Analyze Function
    # --------------------------------------------------
    def analyze(self, logs: str, project_type: str = None) -> Dict:
        error_lines = self.extract_error_lines(logs)

        combined_snippet = "\n".join(error_lines)

        classification = self.classify_error(combined_snippet, project_type)

        return {
            "error_type": classification["error_type"],
            "language": classification.get("language", "unknown"),
            "message": classification["message"],
            "target": classification.get("target"),
            "confidence": classification["confidence"],
            "raw_snippet": combined_snippet,
        }