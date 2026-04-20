"""Tool registry — collects all tools for the agent."""

from src.tools.web_search import web_search
from src.tools.calculator import calculator
from src.tools.wikipedia import wiki_summary, wiki_search

# TODO: Add after team clarification
# from src.tools.document_qa import document_qa
# from src.tools.knowledge_base_lookup import knowledge_base_lookup


def get_all_tools() -> list:
    """Return all available tools for the agent."""
    return [
        web_search,
        calculator,
        wiki_summary,
        wiki_search,
        # document_qa,
        # knowledge_base_lookup,
    ]
