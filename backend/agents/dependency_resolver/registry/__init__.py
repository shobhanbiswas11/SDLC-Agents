from .pypi import PyPIRegistry
from .npm import NPMRegistry
from .maven import MavenRegistry
from .cargo import CargoRegistry
from .base import BaseRegistry

_REGISTRY_MAP = {
    "pypi":  PyPIRegistry,
    "npm":   NPMRegistry,
    "maven": MavenRegistry,
    "cargo": CargoRegistry,
}

def get_registry(ecosystem: str) -> BaseRegistry:
    cls = _REGISTRY_MAP.get(ecosystem)
    if not cls:
        raise ValueError(f"No registry for ecosystem: {ecosystem}")
    return cls()
