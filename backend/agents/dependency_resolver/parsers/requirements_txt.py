"""Parser for Python requirements.txt format."""
import re
from typing import List, Tuple

# Match: name[extras] (op version) , ... ; markers
_REQ_RE = re.compile(
    r"^([A-Za-z0-9_\-\.]+)"          # package name
    r"(?:\[[^\]]*\])?"                # optional extras
    r"((?:\s*[><=!~]{1,3}\s*[\w\.\*]+\s*,?)*)"  # version specifiers
)

class RequirementsTxtParser:
    def parse(self, content: str) -> List[Tuple[str, str]]:
        deps: List[Tuple[str, str]] = []
        for raw in content.splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            line = line.split("#")[0].strip()   # strip inline comment
            line = line.split(";")[0].strip()   # strip env markers
            if not line:
                continue
            m = _REQ_RE.match(line)
            if m:
                name       = m.group(1).strip()
                constraint = m.group(2).strip().rstrip(",") or "*"
                deps.append((name, constraint))
        return deps
