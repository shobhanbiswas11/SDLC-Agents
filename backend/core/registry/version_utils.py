"""
Version constraint parsing and matching utilities
Handles npm and pip version constraints
"""

import re
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)


def parse_version_constraint(constraint: str) -> dict:
    """
    Parse version constraint string into structured format

    Examples:
    - "^1.2.3" (npm caret: >=1.2.3, <2.0.0)
    - "~1.2.3" (npm tilde: >=1.2.3, <1.3.0)
    - "1.2.3" (exact)
    - ">=1.0,<2.0" (range)
    - "*" (any)

    Returns:
        Dict with constraint details
    """
    constraint = constraint.strip()

    if constraint == "*" or constraint == "":
        return {"type": "any", "original": constraint}

    # Handle npm caret (^)
    if constraint.startswith("^"):
        version = constraint[1:]
        return {
            "type": "caret",
            "version": version,
            "original": constraint
        }

    # Handle npm tilde (~)
    if constraint.startswith("~"):
        version = constraint[1:]
        return {
            "type": "tilde",
            "version": version,
            "original": constraint
        }

    # Handle comparison operators
    for op in [">=", "<=", "==", "!=", "~=", ">", "<"]:
        if constraint.startswith(op):
            version = constraint[len(op):]
            return {
                "type": "comparison",
                "operator": op,
                "version": version.strip(),
                "original": constraint
            }

    # Default: treat as exact version
    return {
        "type": "exact",
        "version": constraint,
        "original": constraint
    }


def version_satisfies_constraint(version: str, constraint: str) -> bool:
    """
    Check if a version satisfies a constraint

    Args:
        version: Version string (e.g., "1.2.3")
        constraint: Constraint string (e.g., "^1.0.0", ">=1.0,<2.0")

    Returns:
        True if version satisfies constraint
    """
    constraint = constraint.strip()
    version = version.strip()

    # Handle "any" constraint
    if constraint == "*" or constraint == "":
        return True

    # Handle multiple constraints (comma-separated)
    if "," in constraint:
        parts = [c.strip() for c in constraint.split(",")]
        return all(version_satisfies_constraint(version, c) for c in parts)

    parsed = parse_version_constraint(constraint)

    if parsed["type"] == "any":
        return True

    elif parsed["type"] == "caret":
        # ^ allows changes that don't modify the left-most non-zero digit
        base_version = parsed["version"]
        return _version_in_caret_range(version, base_version)

    elif parsed["type"] == "tilde":
        # ~ allows patch-level changes
        base_version = parsed["version"]
        return _version_in_tilde_range(version, base_version)

    elif parsed["type"] == "comparison":
        op = parsed["operator"]
        constraint_version = parsed["version"]
        return _compare_versions(version, op, constraint_version)

    elif parsed["type"] == "exact":
        return _normalize_version(version) == _normalize_version(parsed["version"])

    return False


def _version_in_caret_range(version: str, base: str) -> bool:
    """Check if version is in caret range (^base)"""
    v = _version_tuple(version)
    b = _version_tuple(base)

    # Caret: >=base, <next major (if major > 0) or <next minor (if major == 0)
    if not _compare_version_tuples(v, ">=", b):
        return False

    # Find the next boundary
    if b[0] > 0:
        # Major version > 0: allow changes up to next major
        return v[0] == b[0]
    elif len(b) > 1 and b[1] > 0:
        # Major == 0, minor > 0: allow changes up to next minor
        return v[0] == 0 and v[1] == b[1]
    else:
        # Major == 0, minor == 0: allow only this exact version
        return v[0] == 0 and v[1] == 0 and v[2] == b[2]


def _version_in_tilde_range(version: str, base: str) -> bool:
    """Check if version is in tilde range (~base)"""
    v = _version_tuple(version)
    b = _version_tuple(base)

    # Tilde: >=base, <next minor
    if not _compare_version_tuples(v, ">=", b):
        return False

    # Must have same major and minor
    return v[0] == b[0] and v[1] == b[1]


def _compare_versions(version: str, op: str, constraint: str) -> bool:
    """Compare two versions using an operator"""
    v = _version_tuple(version)
    c = _version_tuple(constraint)
    return _compare_version_tuples(v, op, c)


def _compare_version_tuples(v: Tuple, op: str, c: Tuple) -> bool:
    """Compare version tuples"""
    if op == "==":
        return v == c
    elif op == "!=":
        return v != c
    elif op == ">":
        return v > c
    elif op == ">=":
        return v >= c
    elif op == "<":
        return v < c
    elif op == "<=":
        return v <= c
    elif op == "~=":
        # Compatible version (PEP 440)
        return v >= c and _versions_compatible(v, c)
    return False


def _versions_compatible(v: Tuple, c: Tuple) -> bool:
    """Check if versions are compatible (PEP 440 ~=)"""
    # Compatible means: same major.minor, higher or equal patch
    return v[0] == c[0] and v[1] == c[1]


def _version_tuple(version: str) -> Tuple[int, int, int]:
    """Convert version string to tuple of integers"""
    version = version.strip().lstrip("v")

    # Extract numeric parts
    parts = []
    for part in version.split("."):
        # Remove non-numeric suffixes (e.g., "3a1" -> 3)
        match = re.match(r"(\d+)", part)
        if match:
            parts.append(int(match.group(1)))
        else:
            parts.append(0)

    # Pad to 3 elements
    while len(parts) < 3:
        parts.append(0)

    return tuple(parts[:3])


def _normalize_version(version: str) -> str:
    """Normalize version string for comparison"""
    return version.strip().lstrip("v").lower()
