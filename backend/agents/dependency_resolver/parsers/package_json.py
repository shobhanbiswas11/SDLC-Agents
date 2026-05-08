"""Parser for Node.js package.json."""
import json
from typing import Dict, List, Tuple


class PackageJsonParser:
    def parse(self, content: str, include_dev: bool = False) -> List[Tuple[str, str]]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid package.json: {e}")
        deps: Dict[str, str] = {}
        deps.update(data.get("dependencies", {}))
        if include_dev:
            deps.update(data.get("devDependencies", {}))
        return list(deps.items())
