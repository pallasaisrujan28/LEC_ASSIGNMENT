"""Wikipedia tool — wikipedia-api (no API key required)."""

from langchain_core.tools import tool


@tool
def wiki_summary(topic: str, sentences: int = 3) -> str:
    """Get a summary of a Wikipedia article by topic name."""
    import wikipediaapi

    wiki = wikipediaapi.Wikipedia(
        user_agent="AgenticSystem/1.0 (production-assignment)",
        language="en",
    )
    page = wiki.page(topic)
    if not page.exists():
        return f"No Wikipedia article found for '{topic}'"

    parts = page.summary.split(". ")
    trimmed = ". ".join(parts[:sentences])
    if not trimmed.endswith("."):
        trimmed += "."
    return trimmed


@tool
def wiki_search(query: str, max_results: int = 5) -> list[str]:
    """Search Wikipedia for articles matching a query. Returns article titles."""
    import wikipediaapi

    wiki = wikipediaapi.Wikipedia(
        user_agent="AgenticSystem/1.0 (production-assignment)",
        language="en",
    )
    page = wiki.page(query)
    if page.exists():
        links = list(page.links.keys())[:max_results]
        return [page.title] + links
    return [f"No results found for '{query}'"]
