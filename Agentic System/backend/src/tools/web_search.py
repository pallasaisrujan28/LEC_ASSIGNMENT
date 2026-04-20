"""Web Search tool — Tavily API.

Tavily is designed for AI agents. Returns clean, structured results
with extracted content. 1,000 free searches/month, no per-minute rate limit.
"""

import os

from langchain_core.tools import tool


@tool
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web for a query. Returns results with title, content, and URL.

    Uses Tavily search API for reliable, AI-optimized results.
    """
    from tavily import TavilyClient

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return [{"title": "Error", "content": "TAVILY_API_KEY not set", "url": ""}]

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(query, max_results=max_results)

        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "url": r.get("url", ""),
            })
        return results if results else [{"title": "No results", "content": f"No results found for: {query}", "url": ""}]

    except Exception as e:
        return [{"title": "Search error", "content": f"Search failed: {str(e)}", "url": ""}]
