"""
Basic license risk checker.
Flags packages whose reported license is in a known restricted set.
"""
from __future__ import annotations
from typing import Dict, List, Optional

_RESTRICTED = {
    "AGPL-3.0", "AGPL-3.0-only", "AGPL-3.0-or-later",
    "GPL-2.0",  "GPL-2.0-only",  "GPL-2.0-or-later",
    "GPL-3.0",  "GPL-3.0-only",  "GPL-3.0-or-later",
    "SSPL-1.0", "Commons-Clause",
}
_PERMISSIVE = {
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
    "ISC", "Unlicense", "0BSD", "CC0-1.0", "LGPL-2.1",
}


class LicenseChecker:
    def check(self, packages: List[Dict]) -> List[Dict[str, str]]:
        """Return list of {package, version, license, risk} for flagged packages."""
        issues: List[Dict[str, str]] = []
        for pkg in packages:
            lic = pkg.get("license")
            if not lic or lic in _PERMISSIVE:
                continue
            if lic in _RESTRICTED:
                issues.append({
                    "package": pkg["name"],
                    "version": pkg["version"],
                    "license": lic,
                    "risk":    "restricted",
                })
            elif lic not in _PERMISSIVE:
                issues.append({
                    "package": pkg["name"],
                    "version": pkg["version"],
                    "license": lic,
                    "risk":    "unknown",
                })
        return issues
