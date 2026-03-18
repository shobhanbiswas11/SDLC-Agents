"""
npm registry client — fetch package metadata from registry.npmjs.org.
"""

from __future__ import annotations

import logging
from typing import Any

from app.utils.cache import cache_get, cache_set
from app.utils.http import get_http_client

logger = logging.getLogger(__name__)

NPM_BASE = "https://registry.npmjs.org"


async def fetch_npm_metadata(package: str, version: str | None = None) -> dict[str, Any] | None:
    """
    Fetch metadata for an npm package.

    If `version` is given, returns that version's metadata;
    otherwise returns the full document (all versions).
    """
    cache_key = f"npm:{package}:{version or 'latest'}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    if version:
        url = f"{NPM_BASE}/{package}/{version}"
    else:
        url = f"{NPM_BASE}/{package}"

    client = await get_http_client()
    try:
        resp = await client.get(url)
        if resp.status_code == 404:
            logger.warning("npm package not found: %s %s", package, version or "")
            return None
        resp.raise_for_status()
        data = resp.json()
        cache_set(cache_key, data)
        return data
    except Exception:
        logger.exception("Error fetching npm metadata for %s", package)
        return None


def extract_npm_dependencies(metadata: dict[str, Any]) -> dict[str, str]:
    """
    Extract `dependencies` from a *version-specific* npm metadata response.
    Returns dict of {name: version_range}.
    """
    return metadata.get("dependencies", {}) or {}


def extract_npm_peer_dependencies(metadata: dict[str, Any]) -> dict[str, str]:
    """
    Extract `peerDependencies` from a version-specific npm metadata response.
    """
    return metadata.get("peerDependencies", {}) or {}


def extract_npm_available_versions(metadata: dict[str, Any]) -> list[str]:
    """
    From the *full* package document, return all version strings.
    """
    return list(metadata.get("versions", {}).keys())
