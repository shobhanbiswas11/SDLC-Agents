"""
PyPI registry client — fetch package metadata from pypi.org.
"""

from __future__ import annotations

import logging
from typing import Any

from app.utils.cache import cache_get, cache_set
from app.utils.http import get_http_client

logger = logging.getLogger(__name__)

PYPI_BASE = "https://pypi.org/pypi"


async def fetch_pypi_metadata(package: str, version: str | None = None) -> dict[str, Any] | None:
    """
    Fetch metadata for a Python package from PyPI.

    If `version` is provided, fetches that specific version;
    otherwise fetches the latest release.

    Returns the full JSON response or None on error.
    """
    cache_key = f"pypi:{package}:{version or 'latest'}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{PYPI_BASE}/{package}/json" if version is None else f"{PYPI_BASE}/{package}/{version}/json"

    client = await get_http_client()
    try:
        resp = await client.get(url)
        if resp.status_code == 404:
            logger.warning("PyPI package not found: %s %s", package, version or "")
            return None
        resp.raise_for_status()
        data = resp.json()
        cache_set(cache_key, data)
        return data
    except Exception:
        logger.exception("Error fetching PyPI metadata for %s", package)
        return None


def extract_requires_dist(metadata: dict[str, Any]) -> list[str]:
    """
    Extract `requires_dist` from PyPI metadata → list of PEP 508 strings.
    """
    return metadata.get("info", {}).get("requires_dist") or []


def extract_available_versions(metadata: dict[str, Any]) -> list[str]:
    """
    Return all release version strings for the package.
    """
    return list(metadata.get("releases", {}).keys())
