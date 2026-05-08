"""
Registry clients for npm and PyPI
Provides abstraction to fetch package data from both registries
"""

from .base import BaseRegistry
from .npm import NPMRegistry
from .pypi import PyPIRegistry

__all__ = ["BaseRegistry", "NPMRegistry", "PyPIRegistry"]
