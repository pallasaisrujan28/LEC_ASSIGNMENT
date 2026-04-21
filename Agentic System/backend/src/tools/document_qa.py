"""Document Q&A tool — retrieves relevant passages from user provided text or uploaded PDFs.

Chunks the document, finds the most relevant passages to the question
using keyword matching, and returns them. The reflector node (main LLM)
generates the final answer from these passages.

If no document_text is provided, checks the session document store
for previously uploaded PDF content.
"""

import re

from langchain_core.tools import tool


def _get_document_store() -> dict:
    """Get the document store from the API module."""
    try:
        from src.api.app import document_store
        return document_store
    except ImportError:
        return {}


def _chunk_and_search(text: str, question: str, max_results: int = 5) -> list[dict]:
    """Chunk text and return most relevant passages for the question."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip() and len(p.strip()) > 20]

    if not paragraphs:
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        paragraphs = []
        for i in range(0, len(sentences), 3):
            chunk = " ".join(sentences[i:i + 3])
            if len(chunk) > 20:
                paragraphs.append(chunk)

    if not paragraphs:
        return [{"passage": text[:500], "relevance": 1}]

    question_words = set(question.lower().split())
    stop_words = {"what", "is", "the", "a", "an", "of", "in", "to", "and", "or",
                  "how", "does", "do", "it", "this", "that", "for", "on", "with", "about"}
    question_keywords = question_words - stop_words

    scored = []
    for p in paragraphs:
        p_lower = p.lower()
        matches = sum(1 for w in question_keywords if w in p_lower)
        scored.append((matches, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:max_results]

    results = [{"passage": passage[:1000], "relevance": score} for score, passage in top]

    if all(r["relevance"] == 0 for r in results):
        results = [{"passage": p[:1000], "relevance": 1} for p in paragraphs[:3]]

    return results


@tool
def document_qa(question: str, document_text: str = "", thread_id: str = "") -> list[dict]:
    """Find relevant passages in a document that answer the question.

    If document_text is provided, searches that text directly.
    If not, checks for a previously uploaded PDF in the session.
    Use when the user asks questions about uploaded documents or provided text.
    """
    text = document_text.strip() if document_text else ""

    if not text and thread_id:
        store = _get_document_store()
        text = store.get(thread_id, "")

    if not text:
        store = _get_document_store()
        if store:
            text = list(store.values())[-1]

    if not text:
        return [{"passage": "No document available. Please upload a PDF or provide document text.", "relevance": 0}]

    return _chunk_and_search(text, question)
