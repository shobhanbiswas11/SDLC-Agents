"""Source-file parsers and language detection."""
from .language_detector import (
    EXTENSION_MAP,
    detect_language,
    get_all_supported_extensions,
)

__all__ = [
    "EXTENSION_MAP",
    "detect_language",
    "get_all_supported_extensions",
]
