"""crates.io registry client (stub — M8)."""
from .base import BaseRegistry
from typing import Dict, List, Optional, Any

class CargoRegistry(BaseRegistry):
    async def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("Cargo registry coming in M8")
    async def get_versions(self, package_name: str) -> List[str]:
        raise NotImplementedError
    async def get_dependencies(self, package_name: str, version: str) -> Dict[str, str]:
        raise NotImplementedError
    async def find_compatible_version(self, package_name: str, constraint: str) -> Optional[str]:
        raise NotImplementedError
