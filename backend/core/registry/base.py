"""
Base registry interface for npm and PyPI
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BaseRegistry(ABC):
    """Abstract base class for package registries"""

    def __init__(self, timeout: int = 30, cache: Optional[Dict] = None):
        """
        Initialize registry client

        Args:
            timeout: HTTP request timeout in seconds
            cache: Optional cache dict for memoization
        """
        self.timeout = timeout
        self.cache = cache or {}

    @abstractmethod
    async def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Get package metadata from registry

        Args:
            package_name: Name of the package

        Returns:
            Dict with package info or None if not found
        """
        pass

    @abstractmethod
    async def get_versions(self, package_name: str) -> List[str]:
        """
        Get all available versions for a package

        Args:
            package_name: Name of the package

        Returns:
            List of version strings (sorted)
        """
        pass

    @abstractmethod
    async def get_dependencies(
        self, package_name: str, version: str
    ) -> Dict[str, str]:
        """
        Get dependencies for a specific package version

        Args:
            package_name: Name of the package
            version: Version of the package

        Returns:
            Dict mapping dependency_name -> version_constraint
        """
        pass

    @abstractmethod
    async def find_compatible_version(
        self, package_name: str, constraint: str
    ) -> Optional[str]:
        """
        Find a version matching the constraint

        Args:
            package_name: Name of the package
            constraint: Version constraint (e.g., "^1.0.0", ">=2.0,<3.0")

        Returns:
            Version string that satisfies constraint, or None
        """
        pass

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        return self.cache.get(key)

    def _set_cache(self, key: str, value: Any) -> None:
        """Set value in cache"""
        self.cache[key] = value

    def _cache_key(self, *parts: str) -> str:
        """Generate cache key from parts"""
        return ":".join(parts)
