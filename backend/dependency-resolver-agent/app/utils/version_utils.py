"""
Version comparison and parsing helpers built on top of `packaging`.
"""

from __future__ import annotations

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version


def parse_version(raw: str) -> Version | None:
    """Attempt to parse a PEP 440 version string; return None on failure."""
    try:
        return Version(raw)
    except InvalidVersion:
        return None


def parse_specifier(raw: str) -> SpecifierSet | None:
    """Parse a PEP 440 specifier set (e.g. '>=1.0,<2'); return None on failure."""
    try:
        return SpecifierSet(raw)
    except InvalidSpecifier:
        return None


def intersect_specifiers(specs: list[str]) -> SpecifierSet | None:
    """
    Intersect multiple specifier strings into a single SpecifierSet.
    Returns None if any specifier is invalid.
    """
    result = SpecifierSet()
    for s in specs:
        parsed = parse_specifier(s)
        if parsed is None:
            return None
        result &= parsed
    return result


def specifiers_conflict(specs: list[str], available_versions: list[str]) -> bool:
    """
    Return True when *no* version in `available_versions` satisfies ALL specifiers.
    We treat this as a conflict.
    """
    combined = intersect_specifiers(specs)
    if combined is None:
        return True  # un-parseable → assume conflict
    versions = [v for raw in available_versions if (v := parse_version(raw)) is not None]
    return not any(v in combined for v in versions)


def latest_compatible(specs: list[str], available_versions: list[str]) -> str | None:
    """
    Return the latest version from `available_versions` that satisfies all `specs`,
    or None when no match exists.
    """
    combined = intersect_specifiers(specs)
    if combined is None:
        return None
    versions = sorted(
        [v for raw in available_versions if (v := parse_version(raw)) is not None],
        reverse=True,
    )
    for v in versions:
        if v in combined:
            return str(v)
    return None
