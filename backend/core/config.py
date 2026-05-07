"""
Legacy compatibility shim — re-exports settings from core.config.base
so older `from core.config import get_settings` imports keep working.
"""
from .config.base import Settings, get_settings  # noqa: F401

__all__ = ["Settings", "get_settings"]
