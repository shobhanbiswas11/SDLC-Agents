"""
PyPI Registry Client
Fetches package information from the Python Package Index (PyPI)
"""

import httpx
import json
import logging
from typing import Dict, List, Optional, Any
from .base import BaseRegistry
from .version_utils import version_satisfies_constraint

logger = logging.getLogger(__name__)


class PyPIRegistry(BaseRegistry):
    """Client for PyPI registry (https://pypi.org)"""

    def __init__(
        self,
        registry_url: str = "https://pypi.org/pypi",
        timeout: int = 30,
        cache: Optional[Dict] = None
    ):
        """
        Initialize PyPI registry client

        Args:
            registry_url: Base URL for PyPI registry
            timeout: Request timeout in seconds
            cache: Optional cache dict
        """
        super().__init__(timeout=timeout, cache=cache)
        self.registry_url = registry_url

    async def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Get full package metadata from PyPI"""
        # Normalize package name (PyPI is case-insensitive, uses hyphens)
        normalized_name = package_name.lower().replace("_", "-")

        cache_key = self._cache_key("pypi", "info", normalized_name)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.registry_url}/{normalized_name}/json"
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                self._set_cache(cache_key, data)
                return data

        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch PyPI package {package_name}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON from PyPI for {package_name}: {e}")
            return None

    async def get_versions(self, package_name: str) -> List[str]:
        """Get all available versions for a PyPI package"""
        info = await self.get_package_info(package_name)
        if not info or "releases" not in info:
            return []

        versions = list(info["releases"].keys())
        # Sort versions (simple approach - proper semver sorting would be better)
        return sorted(versions, key=lambda v: self._version_key(v))

    async def get_dependencies(
        self, package_name: str, version: str
    ) -> Dict[str, str]:
        """Get dependencies for a specific PyPI package version"""
        # Normalize name
        normalized_name = package_name.lower().replace("_", "-")

        cache_key = self._cache_key("pypi", "deps", normalized_name, version)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            info = await self.get_package_info(package_name)
            if not info or "releases" not in info:
                return {}

            # PyPI provides requires_dist in the release info
            releases = info["releases"].get(version, [])
            if not releases:
                logger.warning(f"Version {version} not found for {package_name}")
                return {}

            # Get the info from the first release (usually only one)
            release_info = releases[0] if releases else {}

            # Extract requires_dist if available
            requires_dist = release_info.get("requires_dist", [])
            if isinstance(requires_dist, str):
                requires_dist = [requires_dist]

            # Parse requires_dist to extract dependencies
            deps = self._parse_requires_dist(requires_dist)
            self._set_cache(cache_key, deps)
            return deps

        except Exception as e:
            logger.warning(f"Failed to get dependencies for {package_name}@{version}: {e}")
            return {}

    async def find_compatible_version(
        self, package_name: str, constraint: str
    ) -> Optional[str]:
        """Find a PyPI version matching the constraint"""
        versions = await self.get_versions(package_name)
        if not versions:
            return None

        # Try to find latest version that satisfies constraint
        for version in reversed(versions):  # Newest first
            if version_satisfies_constraint(version, constraint):
                return version

        logger.debug(f"No version found for {package_name} with constraint {constraint}")
        return None

    def _parse_requires_dist(self, requires_dist: List[str]) -> Dict[str, str]:
        """
        Parse requires_dist list from PyPI

        Format: "package; extra == 'dev'" or "package (>=1.0,<2.0)"
        We extract just the package and version constraint
        """
        deps = {}

        for req in requires_dist:
            if not req:
                continue

            # Split on semicolon to remove extras
            req_part = req.split(";")[0].strip()

            # Parse package and version constraint
            # Examples: "django>=3.0", "flask (>=1.0,<2.0)", "requests"
            for op in [">=", "<=", "==", "~=", ">", "<", "!="]:
                if op in req_part:
                    parts = req_part.split(op, 1)
                    package = parts[0].strip()
                    constraint = op + parts[1].strip()
                    deps[package] = constraint
                    break
            else:
                # No operator found
                if "(" in req_part:
                    # Handle format: "package (constraint)"
                    package, rest = req_part.split("(", 1)
                    constraint = rest.rstrip(")")
                    deps[package.strip()] = constraint.strip()
                else:
                    # No constraint
                    deps[req_part] = "*"

        return deps

    def _version_key(self, version: str) -> tuple:
        """Convert version string to sortable tuple (simple approach)"""
        try:
            # Handle semver-like versions (e.g., "1.2.3")
            parts = version.split(".")
            return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])
        except (ValueError, AttributeError):
            return (0, 0, 0)
