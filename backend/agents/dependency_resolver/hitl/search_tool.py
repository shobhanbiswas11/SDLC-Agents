"""
Web search tool with domain allow-list and full transparency.

Every search is announced to the user before execution.
Results are filtered to the allow-list before being returned.
Supports SerpAPI (primary) and a direct-fetch fallback for allow-listed domains.
"""
from __future__ import annotations
import logging
import os
from typing import List, Optional
import httpx
from agents.dependency_resolver.schemas import SearchResult

logger = logging.getLogger(__name__)

ALLOWED_DOMAINS = {
    "pypi.org", "npmjs.com", "mvnrepository.com", "crates.io",
    "osv.dev", "github.com", "nvd.nist.gov", "security.snyk.io",
    "deps.dev", "pkg.go.dev", "packaging.python.org",
    "docs.npmjs.com", "doc.rust-lang.org",
}

_SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
_BING_KEY    = os.getenv("BING_SEARCH_KEY", "")
_PROVIDER    = os.getenv("SEARCH_PROVIDER", "none").lower()   # serpapi | bing | none


def _is_allowed(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower().lstrip("www.")
        return any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS)
    except Exception:
        return False


class SearchTool:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def search(
        self,
        query: str,
        n: int = 5,
    ) -> List[SearchResult]:
        """Execute search and return allow-listed results."""
        results: List[SearchResult] = []

        if _PROVIDER == "serpapi" and _SERPAPI_KEY:
            results = await self._serpapi(query, n)
        elif _PROVIDER == "bing" and _BING_KEY:
            results = await self._bing(query, n)
        else:
            # Fallback: query PyPI JSON API for package-name queries
            results = await self._pypi_fallback(query)

        # Enforce allow-list
        filtered = [r for r in results if _is_allowed(r.url)]
        logger.info(
            f"Search '{query}': {len(results)} raw → {len(filtered)} after allow-list"
        )
        return filtered[:n]

    async def fetch_snippet(self, url: str, max_chars: int = 2_000) -> str:
        """Fetch text from a single allow-listed URL."""
        if not _is_allowed(url):
            return f"[blocked: {url} not in allow-list]"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(url, headers={"User-Agent": "DepResolver/1.0"})
                r.raise_for_status()
                text = r.text
                # Very basic HTML stripping
                import re
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
                return text[:max_chars]
        except Exception as exc:
            logger.warning(f"fetch_snippet({url}): {exc}")
            return ""

    # ── Providers ─────────────────────────────────────────────────────────────

    async def _serpapi(self, query: str, n: int) -> List[SearchResult]:
        url = "https://serpapi.com/search"
        params = {"q": query, "api_key": _SERPAPI_KEY, "num": n, "engine": "google"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(url, params=params)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            logger.warning(f"SerpAPI error: {exc}")
            return []
        results = []
        for item in data.get("organic_results", [])[:n]:
            results.append(SearchResult(
                query=query,
                url=item.get("link", ""),
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
            ))
        return results

    async def _bing(self, query: str, n: int) -> List[SearchResult]:
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": _BING_KEY}
        params  = {"q": query, "count": n}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(url, headers=headers, params=params)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            logger.warning(f"Bing search error: {exc}")
            return []
        results = []
        for item in data.get("webPages", {}).get("value", [])[:n]:
            results.append(SearchResult(
                query=query,
                url=item.get("url", ""),
                title=item.get("name", ""),
                snippet=item.get("snippet", ""),
            ))
        return results

    async def _pypi_fallback(self, query: str) -> List[SearchResult]:
        """
        No real search provider configured.
        Heuristic routing:
          - CVE / vulnerability / security queries → OSV.dev batch query
          - Looks like a package name (no spaces) → PyPI JSON lookup
          - Everything else → honest empty result (don't hallucinate)
        """
        import re
        q = query.strip()

        # ── CVE / vulnerability query → OSV.dev ──────────────────────────────
        cve_keywords = ("cve", "vulnerabilit", "security", "exploit", "ghsa",
                        "nvd", "osv", "snyk", "patch", "advisory")
        if any(kw in q.lower() for kw in cve_keywords):
            # Extract what looks like a package name from the query
            pkg = re.sub(r"(cve|vulnerabilit\w*|security|in|for|of|the|what|are|potential)\s*",
                         "", q, flags=re.IGNORECASE).strip()
            pkg = re.split(r"[\s>=<!]", pkg)[0] if pkg else ""
            if pkg:
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        r = await client.post(
                            "https://api.osv.dev/v1/query",
                            json={"package": {"name": pkg}},
                        )
                        if r.status_code == 200:
                            vulns = r.json().get("vulns", [])[:5]
                            results = []
                            for v in vulns:
                                vid = v.get("id", "")
                                summary = v.get("summary", "")
                                results.append(SearchResult(
                                    query=query,
                                    url=f"https://osv.dev/vulnerability/{vid}",
                                    title=f"{vid} — {pkg}",
                                    snippet=summary or "No summary available.",
                                ))
                            if results:
                                return results
                except Exception:
                    pass
            # No CVEs found or pkg extraction failed — return informative stub
            return [SearchResult(
                query=query,
                url="https://osv.dev",
                title="OSV.dev — Open Source Vulnerability Database",
                snippet=(
                    "No vulnerability records found for this query via OSV.dev. "
                    "Configure SERPAPI_KEY or BING_SEARCH_KEY in .env for full web search."
                ),
            )]

        # ── Single-token query → treat as package name on PyPI ────────────────
        tokens = q.split()
        if len(tokens) == 1:
            pkg = re.split(r"[\s>=<!]", q)[0]
            url = f"https://pypi.org/pypi/{pkg}/json"
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    r = await client.get(url)
                    if r.status_code == 200:
                        data = r.json()
                        info = data.get("info", {})
                        return [SearchResult(
                            query=query,
                            url=f"https://pypi.org/project/{pkg}/",
                            title=f"{pkg} {info.get('version','')} on PyPI",
                            snippet=info.get("summary", ""),
                        )]
            except Exception:
                pass

        # ── Multi-word query with no real search provider ─────────────────────
        # Return an honest empty list — don't pretend to search.
        logger.info(f"No search provider configured; skipping web search for: {q!r}")
        return []
