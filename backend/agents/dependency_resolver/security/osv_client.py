"""
OSV.dev vulnerability client.
Queries https://api.osv.dev/v1/query for CVE/GHSA records.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

OSV_QUERY_URL = "https://api.osv.dev/v1/query"
OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
_ECOSYSTEM_MAP = {
    "pypi":  "PyPI",
    "npm":   "npm",
    "maven": "Maven",
    "cargo": "crates.io",
}


class OSVClient:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    async def query_package(
        self, name: str, version: str, ecosystem: str
    ) -> List[str]:
        """Return list of vulnerability IDs (CVE/GHSA) for a package@version."""
        osv_eco = _ECOSYSTEM_MAP.get(ecosystem, ecosystem)
        payload = {
            "version": version,
            "package": {"name": name, "ecosystem": osv_eco},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(OSV_QUERY_URL, json=payload)
                if r.status_code != 200:
                    return []
                data = r.json()
                return [v["id"] for v in data.get("vulns", [])]
        except Exception as exc:
            logger.warning(f"OSV query failed for {name}@{version}: {exc}")
            return []

    async def annotate_packages(
        self, packages: List[Dict], ecosystem: str
    ) -> List[Dict]:
        """
        Add 'vulnerabilities' list to each package dict.
        Runs queries concurrently (max 10 at a time to be respectful).
        """
        sem = asyncio.Semaphore(10)

        async def _query(pkg: Dict) -> Dict:
            async with sem:
                ids = await self.query_package(
                    pkg["name"], pkg["version"], ecosystem
                )
                pkg["vulnerabilities"] = ids
                return pkg

        results = await asyncio.gather(*[_query(p) for p in packages])
        return list(results)
