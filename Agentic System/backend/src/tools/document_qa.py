"""Document Q&A tool — retrieves relevant passages from user-provided text.

Chunks the document, finds the most relevant passages to the question
using simple keyword/semantic matching, and returns them. The reflector
node (main LLM) generates the final answer from these passages.
"""

from langchain_core.tools import tool


@tool
def document_qa(question: str, document_text: str) -> list[dict]:
    """Find relevant passages in the provided document text that answer the question.

    Chunks the document and returns the most relevant passages.
    Use when the user provides text content and asks questions about it.
    The agent's reflector will synthesize the final answer from these passages.
    """
    if not document_text or not document_text.strip():
        return [{"passage": "No document text provided.", "relevance": 0}]

    # Chunk the document into paragraphs
    paragraphs = [p.strip() for p in document_text.split("\n") if p.strip() and len(p.strip()) > 20]

    # If no paragraphs, try splitting by sentences
    if not paragraphs:
        import re
        sentences = re.split(r'(?<=[.!?])\s+', document_text.strip())
        # Group sentences into chunks of ~3
        paragraphs = []
        for i in range(0, len(sentences), 3):
            chunk = " ".join(sentences[i:i+3])
            if len(chunk) > 20:
                paragraphs.append(chunk)

    if not paragraphs:
        return [{"passage": document_text[:500], "relevance": 1}]

    # Score each paragraph by keyword overlap with the question
    question_words = set(question.lower().split())
    # Remove common stop words
    stop_words = {"what", "is", "the", "a", "an", "of", "in", "to", "and", "or", "how", "does", "do", "it", "this", "that", "for", "on", "with", "about"}
    question_keywords = question_words - stop_words

    scored = []
    for p in paragraphs:
        p_lower = p.lower()
        # Count keyword matches
        matches = sum(1 for w in question_keywords if w in p_lower)
        scored.append((matches, p))

    # Sort by relevance (most matches first), take top 5
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:5]

    results = []
    for score, passage in top:
        results.append({
            "passage": passage[:1000],  # Cap passage length
            "relevance": score,
        })

    # If no keyword matches at all, return first few paragraphs as context
    if all(r["relevance"] == 0 for r in results):
        results = [{"passage": p[:1000], "relevance": 1} for p in paragraphs[:3]]

    return results
