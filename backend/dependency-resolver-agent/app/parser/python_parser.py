"""
Python dependency parser — handles requirements.txt, pyproject.toml, setup.py/cfg.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass
class Dependency:
    """A single parsed dependency."""

    name: str
    specifier: str = ""  # e.g. ">=1.0,<2"
    extras: list[str] = field(default_factory=list)
    source_file: str = ""
    ecosystem: str = "python"


# ── requirements.txt ──────────────────────────────────────────


_REQ_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)"
    r"(?:\[(?P<extras>[A-Za-z0-9_,. -]+)\])?"
    r"(?P<spec>[><=!~].+)?$"
)


def _parse_requirements_txt(path: Path) -> list[Dependency]:
    deps: list[Dependency] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        m = _REQ_RE.match(line)
        if m:
            extras = [e.strip() for e in m.group("extras").split(",")] if m.group("extras") else []
            deps.append(
                Dependency(
                    name=m.group("name"),
                    specifier=(m.group("spec") or "").strip(),
                    extras=extras,
                    source_file=str(path),
                )
            )
    return deps


# ── pyproject.toml ────────────────────────────────────────────


def _parse_pep508(raw: str) -> Dependency:
    """Parse a PEP 508 dependency string."""
    m = _REQ_RE.match(raw.strip())
    if m:
        extras = [e.strip() for e in m.group("extras").split(",")] if m.group("extras") else []
        return Dependency(
            name=m.group("name"),
            specifier=(m.group("spec") or "").strip(),
            extras=extras,
        )
    # Fallback — just the name
    return Dependency(name=raw.strip().split(";")[0].strip())


def _parse_pyproject_toml(path: Path) -> list[Dependency]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    deps: list[Dependency] = []

    # [project].dependencies
    for raw in data.get("project", {}).get("dependencies", []):
        d = _parse_pep508(raw)
        d.source_file = str(path)
        deps.append(d)

    # [project.optional-dependencies]
    for _group, items in data.get("project", {}).get("optional-dependencies", {}).items():
        for raw in items:
            d = _parse_pep508(raw)
            d.source_file = str(path)
            deps.append(d)

    return deps


# ── setup.py (best-effort regex) ─────────────────────────────

_INSTALL_REQUIRES_RE = re.compile(
    r"install_requires\s*=\s*\[([^\]]+)\]", re.DOTALL
)


def _parse_setup_py(path: Path) -> list[Dependency]:
    content = path.read_text(encoding="utf-8")
    m = _INSTALL_REQUIRES_RE.search(content)
    if not m:
        return []
    deps: list[Dependency] = []
    for item in re.findall(r"""['"]([^'"]+)['"]""", m.group(1)):
        d = _parse_pep508(item)
        d.source_file = str(path)
        deps.append(d)
    return deps


# ── Public API ────────────────────────────────────────────────


def parse_python_deps(paths: list[Path]) -> list[Dependency]:
    """
    Parse all Python dependency files and return a flat list of Dependency objects.
    """
    all_deps: list[Dependency] = []
    for p in paths:
        if p.name == "requirements.txt":
            all_deps.extend(_parse_requirements_txt(p))
        elif p.name == "pyproject.toml":
            all_deps.extend(_parse_pyproject_toml(p))
        elif p.name in ("setup.py", "setup.cfg"):
            all_deps.extend(_parse_setup_py(p))
    return all_deps
