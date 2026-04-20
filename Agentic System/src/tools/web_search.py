"""Web Search tool — DuckDuckGo (no API key required)."""

import re
import urllib.request

from langchain_core.tools import tool


@tool
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web for a query. Returns results with title, snippet, URL, and page content."""
    from duckduckgo_search import DDGS

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            url = r.get("href", "")
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": url,
                "content": _fetch_page_content(url) if url else "",
            })
    return results


def _fetch_page_content(url: str, max_chars: int = 2000) -> str:
    """Fetch and extract readable text from a URL."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgenticSystem/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception:
        return ""
