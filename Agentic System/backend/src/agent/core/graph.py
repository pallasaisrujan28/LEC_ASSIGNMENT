"""LangGraph graph definition — wires planner, executor, reflector nodes.

Flow: START → planner → executor → reflector → (done? END : planner)

Guards:
- Max 8 iterations (prevents infinite loops)
- Budget cap checked before each LLM call
- Repeated plan detection (same plan twice = force stop)
"""

from langgraph.graph import StateGraph, END

from langchain_core.messages import HumanMessage, AIMessage

from src.agent.core.state import AgentState, BudgetInfo
from src.agent.core.memory import get_checkpointer, maybe_summarize
from src.agent.nodes.planner import planner_node
from src.agent.nodes.executor import executor_node
from src.agent.nodes.reflector import reflector_node

MAX_ITERATIONS = 8


def _should_continue(state: AgentState) -> str:
    """Decide whether to continue or stop after reflection."""
    # If we have a final answer, we're done
    if state.get("final_answer"):
        return "end"

    # If we've hit max iterations, force stop
    if state["iteration"] >= MAX_ITERATIONS:
        return "end"

    # If budget is exhausted, force stop
    if state["budget"].total_cost_usd >= state["budget"].max_budget_usd:
        return "end"

    # Otherwise, re-plan
    return "replan"


def build_graph():
    """Build and compile the Plan-and-Execute agent graph."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("reflector", reflector_node)

    # Define edges
    graph.set_entry_point("planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "reflector")

    # Conditional edge from reflector
    graph.add_conditional_edges(
        "reflector",
        _should_continue,
        {
            "end": END,
            "replan": "planner",
        },
    )

    # Compile with checkpointer
    checkpointer = get_checkpointer()
    return graph.compile(checkpointer=checkpointer)


def run_agent(query: str, budget_usd: float = 20.0, thread_id: str = "default") -> dict:
    """Run the agent on a query and return the full result.

    Returns:
        dict with: query, plan, observations, final_answer, budget, iterations
    """
    graph = build_graph()

    initial_state: AgentState = {
        "query": query,
        "messages": [HumanMessage(content=query)],
        "plan": None,
        "observations": [],
        "reflections": [],
        "iteration": 0,
        "budget": BudgetInfo(max_budget_usd=budget_usd),
        "final_answer": None,
        "error": None,
    }

    config = {"configurable": {"thread_id": thread_id, "actor_id": "agentic-system"}}

    try:
        # First, check if there's existing state (previous conversation)
        existing = graph.get_state(config)
        if existing and existing.values and existing.values.get("messages"):
            # Thread has history — update with new human message and reset per-turn fields
            graph.update_state(config, {
                "query": query,
                "messages": [HumanMessage(content=query)],
                "plan": None,
                "observations": [],
                "reflections": [],
                "iteration": 0,
                "budget": BudgetInfo(max_budget_usd=budget_usd),
                "final_answer": None,
                "error": None,
            })
            result = graph.invoke(None, config=config)
        else:
            # Fresh thread — use initial state
            result = graph.invoke(initial_state, config=config)
    except Exception as e:
        result = {**initial_state, "error": str(e)}

    # Save the AI response and maybe summarize old messages
    final_answer = result.get("final_answer", "")
    if final_answer and not result.get("error"):
        try:
            # Add AI message
            graph.update_state(config, {"messages": [AIMessage(content=final_answer)]})
            # Summarize if messages are getting long
            current_state = graph.get_state(config)
            if current_state and current_state.values.get("messages"):
                summarized = maybe_summarize(current_state.values["messages"])
                if len(summarized) != len(current_state.values["messages"]):
                    graph.update_state(config, {"messages": summarized})
        except Exception:
            pass
    #         save_exchange("agentic-system", thread_id, query, final_answer)
    #     except Exception:
    #         pass

    # Build response
    plan_output = None
    if result.get("plan"):
        plan_output = {
            "thought": result["plan"].thought,
            "steps": [
                {
                    "step_id": s.step_id,
                    "tool": s.tool,
                    "args": s.args,
                    "depends_on": s.depends_on,
                    "reason": s.reason,
                }
                for s in result["plan"].steps
            ],
        }

    observations_output = []
    for o in result.get("observations", []):
        observations_output.append({
            "step_id": o.step_id,
            "tool": o.tool,
            "success": o.success,
            "result": o.result,
            "error": o.error,
        })

    return {
        "query": query,
        "plan": plan_output,
        "observations": observations_output,
        "final_answer": result.get("final_answer", "Agent could not produce an answer."),
        "reflections": result.get("reflections", []),
        "iterations": result.get("iteration", 0),
        "budget": result["budget"].model_dump() if hasattr(result.get("budget"), "model_dump") else {},
        "error": result.get("error"),
    }
