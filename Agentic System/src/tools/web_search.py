"""Web Search tool — DuckDuckGo (no API key required).

Features:
- In-memory cache: same query never hits DuckDuckGo twice
- Proxy support via WEB_SEARCH_PROXY env var
- Retry with backoff on rate limiting
"""

import os
import time
from functools import lru_cache

from langchain_core.tools import tool

# Cache: query → results (survives across tool calls within the same process)
_cache: dict[str, list[dict]] = {}


def _search_ddg(query: str, max_results: int = 5) -> list[dict]:
    """Raw DuckDuckGo search with proxy and retry support."""
    from duckduckgo_search import DDGS

    proxy = os.environ.get("WEB_SEARCH_PROXY")  # e.g. "socks5://127.0.0.1:9050"

    for attempt in range(3):
        try:
            with DDGS(proxy=proxy) as ddgs:
                results = []
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", ""),
                    })
                if results:
                    return results
        except Exception:
            pass
        time.sleep(1 * (attempt + 1))  # backoff: 1s, 2s, 3s

    return []


@tool
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web for a query. Returns results with title, snippet, and URL.

    Results are cached — the same query will return cached results instantly.
    """
    cache_key = f"{query}:{max_results}"

    if cache_key in _cache:
        return _cache[cache_key]

    results = _search_ddg(query, max_results)

    if not results:
        results = [{
            "title": "Search unavailable",
            "snippet": f"Web search returned no results for: {query}. The search service may be temporarily unavailable.",
            "url": "",
        }]

    _cache[cache_key] = results
    return results
