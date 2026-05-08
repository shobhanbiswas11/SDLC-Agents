"""
NPM Registry Client
Fetches package information from the npm registry (npmjs.org)
"""

import httpx
import json
import logging
from typing import Dict, List, Optional, Any
from .base import BaseRegistry
from .version_utils import parse_version_constraint, version_satisfies_constraint

logger = logging.getLogger(__name__)


class NPMRegistry(BaseRegistry):
    """Client for npm registry (https://registry.npmjs.org)"""

    def __init__(
        self,
        registry_url: str = "https://registry.npmjs.org",
        timeout: int = 30,
        cache: Optional[Dict] = None
    ):
        """
        Initialize npm registry client

        Args:
            registry_url: Base URL for npm registry
            timeout: Request timeout in seconds
            cache: Optional cache dict
        """
        super().__init__(timeout=timeout, cache=cache)
        self.registry_url = registry_url

    async def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Get full package metadata from npm registry"""
        cache_key = self._cache_key("npm", "info", package_name)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.registry_url}/{package_name}"
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                self._set_cache(cache_key, data)
                return data

        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch npm package {package_name}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON from npm for {package_name}: {e}")
            return None

    async def get_versions(self, package_name: str) -> List[str]:
        """Get all available versions for an npm package"""
        info = await self.get_package_info(package_name)
        if not info or "versions" not in info:
            return []

        versions = list(info["versions"].keys())
        # Sort versions (simple approach - proper semver sorting would be better)
        return sorted(versions, key=lambda v: self._version_key(v))

    async def get_dependencies(
        self, package_name: str, version: str
    ) -> Dict[str, str]:
        """Get dependencies for a specific npm package version"""
        cache_key = self._cache_key("npm", "deps", package_name, version)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        try:
            info = await self.get_package_info(package_name)
            if not info or "versions" not in info:
                return {}

            version_data = info["versions"].get(version)
            if not version_data:
                logger.warning(f"Version {version} not found for {package_name}")
                return {}

            deps = version_data.get("dependencies", {})
            self._set_cache(cache_key, deps)
            return deps

        except Exception as e:
            logger.warning(f"Failed to get dependencies for {package_name}@{version}: {e}")
            return {}

    async def find_compatible_version(
        self, package_name: str, constraint: str
    ) -> Optional[str]:
        """Find an npm version matching the constraint"""
        versions = await self.get_versions(package_name)
        if not versions:
            return None

        # Try to find latest version that satisfies constraint
        for version in reversed(versions):  # Newest first
            if version_satisfies_constraint(version, constraint):
                return version

        logger.debug(f"No version found for {package_name} with constraint {constraint}")
        return None

    def _version_key(self, version: str) -> tuple:
        """Convert version string to sortable tuple (simple approach)"""
        try:
            # Handle semver-like versions (e.g., "1.2.3")
            parts = version.lstrip('v').split('.')
            return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])
        except (ValueError, AttributeError):
            return (0, 0, 0)
