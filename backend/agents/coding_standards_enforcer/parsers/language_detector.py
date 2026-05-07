"""File-extension → language mapping used by the scanner and the editor."""
from __future__ import annotations

from typing import Optional


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

SKIP_DIRS = {
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
    ".idea",
    ".vscode",
    ".gradle",
    ".mvn",
}


def detect_language(filename: str) -> Optional[str]:
    """Return the language key for a filename, or None when unsupported."""
    lower = filename.lower()
    for ext, lang in EXTENSION_MAP.items():
        if lower.endswith(ext):
            return lang
    return None


def get_all_supported_extensions() -> set:
    """Return all supported file extensions."""
    return set(EXTENSION_MAP.keys())
