"""Planner node — LLM creates a structured plan with steps + dependencies.

The planner is smart about tool selection: it only includes tools that are
actually needed for the query. It does NOT blindly use all available tools.
"""

import logging

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage

from src.agent.core.state import AgentState, Plan, PlanStep

logger = logging.getLogger("agent.planner")
from src.agent.core.budget import BudgetTracker
from pathlib import Path

# Load the improved v2 prompt from file
_prompt_path = Path(__file__).resolve().parent.parent.parent / "prompts" / "v2_improved.txt"
PLANNER_SYSTEM_PROMPT = _prompt_path.read_text()

REPLAN_TEMPLATE = """Previous plan results:
{observations}

The previous plan did not fully answer the query. Create a NEW plan for the remaining work.
Only include steps that still need to be done. Do NOT repeat completed steps.
"""


def _get_llm():
    """Get the Bedrock LLM for planning (no guardrails — internal step)."""
    import os

    return ChatBedrockConverse(
        model=os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"),
        region_name=os.environ.get("AWS_REGION", "us-west-2"),
    )


def planner_node(state: AgentState) -> dict:
    """Generate or revise a plan based on the current state."""
    logger.info(f"[PLANNER] Query: {state['query']}")
    logger.info(f"[PLANNER] Iteration: {state['iteration']}, Observations: {len(state['observations'])}")

    llm = _get_llm()
    budget = BudgetTracker(state["budget"].max_budget_usd)
    budget.info = state["budget"]
    budget.check_budget()

    messages = [SystemMessage(content=PLANNER_SYSTEM_PROMPT)]

    # Include conversation history from previous turns
    from src.agent.core.memory import get_conversation_context

    history = get_conversation_context(state.get("messages", []))
    if history:
        logger.info(f"[PLANNER] Conversation history found ({len(history)} chars)")
        messages.append(SystemMessage(
            content=f"CONVERSATION HISTORY:\n{history}\n\nUse this context to understand references like 'it', 'that', 'earlier', etc."
        ))

    # If we have previous observations, this is a re-plan
    if state["observations"]:
        obs_text = "\n".join(
            f"- {o.step_id} ({o.tool}): {'SUCCESS' if o.success else 'FAILED'} — {o.result or o.error}"
            for o in state["observations"]
        )
        logger.info(f"[PLANNER] Re-planning with {len(state['observations'])} observations")
        messages.append(
            HumanMessage(
                content=REPLAN_TEMPLATE.format(observations=obs_text)
                + f"\n\nOriginal query: {state['query']}"
            )
        )
    else:
        messages.append(HumanMessage(content=state["query"]))

    # Get structured plan from LLM
    structured_llm = llm.with_structured_output(Plan)
    plan = structured_llm.invoke(messages)

    # Handle None — structured output parsing failed
    if plan is None:
        logger.warning("[PLANNER] Structured output returned None — retrying")
        plan = Plan(thought="Could not parse a plan. Will answer directly.", steps=[])

    # Tool abuse prevention guardrail
    from src.agent.core.guardrails import validate_plan
    try:
        validate_plan(plan)
    except Exception as e:
        logger.warning(f"[PLANNER] Plan rejected by guardrail: {e}")
        plan = Plan(thought=str(e), steps=[])

    logger.info(f"[PLANNER] Plan thought: {plan.thought}")
    for step in plan.steps:
        logger.info(f"[PLANNER] Step {step.step_id}: tool={step.tool}, args={step.args}, depends_on={step.depends_on}")

    # Track token usage
    budget.record_usage(
        input_tokens=sum(len(m.content) // 4 for m in messages),
        output_tokens=len(plan.model_dump_json()) // 4,
    )

    return {
        "plan": plan,
        "budget": budget.info,
        "iteration": state["iteration"] + 1,
    }
