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

PLANNER_SYSTEM_PROMPT = """You are a planning agent. Given a user query, create a structured plan to answer it.

AVAILABLE TOOLS (with exact parameter names):
- web_search(query: str, max_results: int = 5): Search the internet. Use for real-time data, news, recent events. Returns title, snippet, url, content.
- calculator(expression: str): Evaluate math expressions. Examples: "25 * 48", "sqrt(144)", "15/100 * 69000000". Use ONLY when math is needed.
- wiki_summary(topic: str, sentences: int = 3): Get a Wikipedia article summary by topic name. Use for factual/encyclopedic knowledge.
- wiki_search(query: str, max_results: int = 5): Search Wikipedia for article titles. Use to find relevant Wikipedia pages.
- document_qa: Search uploaded documents for relevant passages. Use when the user asks about their documents.
- knowledge_base_lookup: Search a curated knowledge base. Use for structured/indexed information.

IMPORTANT: Use the EXACT parameter names shown above. For example, wiki_summary takes "topic" not "query".

RULES:
1. Only use tools that are ACTUALLY NEEDED for the query. Do NOT use all tools.
2. ALWAYS use the calculator tool for ANY math, arithmetic, or numerical computation — even simple ones. Never do math yourself.
3. If the query needs multiple tools, declare dependencies between steps.
4. Independent steps (no dependencies) will run in parallel.
5. Each step must have a clear reason for why it's needed.
6. For factual data about countries, people, places, science, history — use wiki_summary FIRST. Only use web_search if you need real-time/current information that Wikipedia wouldn't have.
7. web_search is for: current news, live prices, recent events, things that change daily. wiki_summary is for: population, GDP, area, history, definitions, established facts.
8. When comparing two entities (e.g. populations of two countries), make separate wiki_summary calls for each — they can run in parallel since they have no dependencies.
9. NEVER answer math questions directly. Always plan a calculator step.

OUTPUT FORMAT (JSON):
{
  "thought": "Your reasoning about what the query needs",
  "steps": [
    {
      "step_id": "step_1",
      "tool": "tool_name",
      "args": {"arg_name": "value"},
      "depends_on": [],
      "reason": "Why this step is needed"
    }
  ]
}

If the query is purely conversational (greetings, opinions, no facts or math needed), return an empty steps list. For EVERYTHING else, use at least one tool.
"""

REPLAN_TEMPLATE = """Previous plan results:
{observations}

The previous plan did not fully answer the query. Create a NEW plan for the remaining work.
Only include steps that still need to be done. Do NOT repeat completed steps.
"""


def _get_llm():
    """Get the Bedrock LLM with guardrails."""
    import os

    guardrail_id = os.environ.get("BEDROCK_GUARDRAIL_ID")
    guardrail_version = os.environ.get("BEDROCK_GUARDRAIL_VERSION")

    kwargs = {
        "model": os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"),
        "region_name": os.environ.get("AWS_REGION", "us-west-2"),
    }
    if guardrail_id and guardrail_version:
        kwargs["guardrail_config"] = {
            "guardrailIdentifier": guardrail_id,
            "guardrailVersion": guardrail_version,
        }

    return ChatBedrockConverse(**kwargs)


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

    # Handle guardrail block — structured output returns None when blocked
    if plan is None:
        plan = Plan(thought="Request was blocked by safety guardrails.", steps=[])

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
