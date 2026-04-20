"""Reflector node — LLM reviews observations, decides: answer or re-plan.

The reflector synthesizes all tool results and either:
1. Produces a final answer (if enough info is available)
2. Requests a re-plan (if more work is needed)
"""

import logging
import os

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from src.agent.core.state import AgentState
from src.agent.core.budget import BudgetTracker

logger = logging.getLogger("agent.reflector")

REFLECTOR_SYSTEM_PROMPT = """You are a reflection agent. You review the results of tool executions and decide what to do next.

Given the original query and tool results, you must either:
1. Provide a FINAL ANSWER if you have enough information
2. Request a RE-PLAN if more work is needed (explain what's missing)

CRITICAL RULES FOR YOUR FINAL ANSWER:
- ONLY include information that directly answers the user's query. Nothing extra.
- Summarize and synthesize tool results — do NOT copy raw tool output.
- If the user asked "What is X and what is Y?", answer X and Y. That's it.
- Do NOT include background context, historical trends, or tangential facts unless the user asked for them.
- Keep the answer short and focused. 2-4 sentences for simple queries, a few paragraphs max for complex ones.
- If a tool returned noisy/irrelevant data, extract only the relevant parts.
- If some tools failed but you have enough info from others, still provide an answer.
- Only request a re-plan if critical information is missing.
"""


class ReflectionResult(BaseModel):
    """Output of the reflector."""

    is_done: bool = Field(description="True if we can provide a final answer")
    final_answer: str | None = Field(
        default=None, description="The final answer if is_done=True"
    )
    feedback: str | None = Field(
        default=None,
        description="Feedback for re-planning if is_done=False",
    )


def _get_llm():
    return ChatBedrockConverse(
        model=os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"),
        region_name=os.environ.get("AWS_REGION", "us-west-2"),
    )


def reflector_node(state: AgentState) -> dict:
    """Review observations and decide: answer or re-plan."""
    logger.info(f"[REFLECTOR] Reviewing {len(state['observations'])} observations, iteration={state.get('iteration', 0)}")

    llm = _get_llm()
    budget = BudgetTracker(state["budget"].max_budget_usd)
    budget.info = state["budget"]
    budget.check_budget()

    # Build context from observations
    obs_text = "\n".join(
        f"- {o.step_id} ({o.tool}): {'SUCCESS' if o.success else 'FAILED'}\n  Result: {o.result or o.error}"
        for o in state["observations"]
    )

    plan_text = ""
    if state["plan"]:
        plan_text = f"Plan thought: {state['plan'].thought}\nSteps: {', '.join(s.tool for s in state['plan'].steps)}"

    # Include conversation history so reflector knows about past turns
    from src.agent.core.memory import get_conversation_context

    history = get_conversation_context(state.get("messages", []))
    history_section = ""
    if history:
        history_section = f"\n\nCONVERSATION HISTORY:\n{history}\n"

    # Force answer after 2+ iterations
    iteration = state.get("iteration", 0)
    force_answer = iteration >= 2

    prompt_suffix = ""
    if force_answer:
        prompt_suffix = f"\n\nIMPORTANT: This is iteration {iteration}. You MUST provide a final answer now using whatever information you have. Do NOT request a re-plan. Answer with partial information if needed."

    messages = [
        SystemMessage(content=REFLECTOR_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Original query: {state['query']}{history_section}\n{plan_text}\n\nTool results:\n{obs_text}{prompt_suffix}"
        ),
    ]

    structured_llm = llm.with_structured_output(ReflectionResult)
    result = structured_llm.invoke(messages)

    logger.info(f"[REFLECTOR] is_done={result.is_done}, answer={str(result.final_answer)[:100] if result.final_answer else 'None'}")
    if result.feedback:
        logger.info(f"[REFLECTOR] Feedback: {result.feedback[:200]}")

    # Track usage
    budget.record_usage(
        input_tokens=sum(len(m.content) // 4 for m in messages),
        output_tokens=100,  # estimate
    )

    reflections = list(state.get("reflections", []))
    if result.feedback:
        reflections.append(result.feedback)

    output = {
        "budget": budget.info,
        "reflections": reflections,
    }

    if result.is_done:
        output["final_answer"] = result.final_answer
    else:
        output["final_answer"] = None

    return output
