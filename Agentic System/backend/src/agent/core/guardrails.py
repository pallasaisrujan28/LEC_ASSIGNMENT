"""Custom guardrails — tool abuse prevention, output sanitization, grounding check.

These run in the agent code, complementing the Bedrock-managed guardrails.
"""

import logging
import re

logger = logging.getLogger("agent.guardrails")

MAX_PLAN_STEPS = 8
MAX_QUERY_LENGTH = 3000


class GuardrailError(Exception):
    """Raised when a guardrail blocks the request."""
    pass


# ── Input validation ────────────────────────────────────────────────────

def validate_input(query: str) -> str:
    """Validate and sanitize user input."""
    if not query or not query.strip():
        raise GuardrailError("Query cannot be empty.")

    query = query.strip()
    if len(query) > MAX_QUERY_LENGTH:
        raise GuardrailError(f"Query too long ({len(query)} chars). Maximum is {MAX_QUERY_LENGTH}.")

    return query


# ── Tool abuse prevention ───────────────────────────────────────────────

def validate_plan(plan) -> None:
    """Reject plans that are too large or suspicious.

    Prevents:
    - Plans with too many steps (likely hallucinated or looping)
    - Plans calling the same tool repeatedly with identical args
    - Plans with unknown tool names
    """
    if not plan or not plan.steps:
        return

    # Too many steps
    if len(plan.steps) > MAX_PLAN_STEPS:
        raise GuardrailError(
            f"Plan has {len(plan.steps)} steps (max {MAX_PLAN_STEPS}). "
            "This looks like a runaway plan. Simplify your query."
        )

    # Duplicate tool calls with same args
    seen = set()
    for step in plan.steps:
        key = f"{step.tool}:{sorted(step.args.items())}"
        if key in seen:
            logger.warning(f"[GUARDRAIL] Duplicate tool call detected: {step.tool} with {step.args}")
            raise GuardrailError(
                f"Plan contains duplicate tool call: {step.tool}. "
                "The agent is repeating itself."
            )
        seen.add(key)

    # Valid tool names
    valid_tools = {"web_search", "calculator", "wiki_summary", "wiki_search", "document_qa", "knowledge_base_lookup"}
    for step in plan.steps:
        if step.tool not in valid_tools:
            logger.warning(f"[GUARDRAIL] Unknown tool in plan: {step.tool}")
            raise GuardrailError(f"Unknown tool: {step.tool}")


# ── Output sanitization ────────────────────────────────────────────────

def sanitize_output(text: str) -> str:
    """Clean the final answer before sending to the user.

    Removes:
    - Raw HTML/script tags
    - Internal tool error traces
    - System prompt leaks
    """
    if not text:
        return text

    # Strip HTML tags
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)

    # Remove common internal leak patterns
    text = re.sub(r"(?i)(system prompt|PLANNER_SYSTEM_PROMPT|REFLECTOR_SYSTEM_PROMPT).*", "", text)
    text = re.sub(r"(?i)traceback \(most recent call last\).*", "", text, flags=re.DOTALL)
    text = re.sub(r"(?i)error:.*?exception.*?\n", "", text)

    # Remove excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ── Grounding check (code-level) ───────────────────────────────────────

def check_grounding(answer: str, observations: list) -> str:
    """Warn if the answer doesn't reference any tool results.

    This is a lightweight code-level check. The Bedrock guardrail
    does the heavy lifting with its contextual grounding filter.
    """
    if not observations or not answer:
        return answer

    # Check if at least one tool result snippet appears in the answer
    successful_results = [
        str(o.result)[:50] for o in observations
        if o.success and o.result
    ]

    if successful_results and not any(
        snippet.lower()[:20] in answer.lower()
        for snippet in successful_results
        if len(snippet) > 10
    ):
        logger.warning("[GUARDRAIL] Answer may not be grounded in tool results")

    return answer
