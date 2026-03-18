"""
Thin wrapper around diskcache for caching registry metadata.
"""

from __future__ import annotations

import json
from typing import Any

import diskcache

from app.config import get_settings

_cache: diskcache.Cache | None = None


def _get_cache() -> diskcache.Cache:
    global _cache
    if _cache is None:
        settings = get_settings()
        _cache = diskcache.Cache(settings.cache_dir)
    return _cache


def cache_get(key: str) -> Any | None:
    """Return cached value or None."""
    c = _get_cache()
    raw = c.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    """Store value in cache with optional TTL (seconds)."""
    c = _get_cache()
    settings = get_settings()
    c.set(key, json.dumps(value), expire=ttl or settings.cache_ttl)


def cache_clear() -> None:
    """Purge the entire cache."""
    c = _get_cache()
    c.clear()
