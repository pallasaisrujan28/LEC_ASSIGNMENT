"""FastAPI application — POST /agent/query + POST /agent/stream endpoints."""

import json
import os
import sys
import uuid

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agent.core.graph import run_agent, build_graph
from src.agent.core.state import AgentState, BudgetInfo

app = FastAPI(
    title="Production Agentic System",
    description="Plan-and-Execute agent with 5+ tools",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    budget_limit: float = Field(default=20.0, description="Max budget in USD")
    thread_id: str = Field(default="", description="Session thread ID")


class QueryResponse(BaseModel):
    query: str
    plan: dict | None = None
    observations: list = []
    final_answer: str | None = None
    reflections: list = []
    iterations: int = 0
    budget: dict = {}
    error: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/agent/query", response_model=QueryResponse)
def agent_query(request: QueryRequest):
    try:
        thread_id = request.thread_id or f"q-{uuid.uuid4().hex[:8]}"
        result = run_agent(
            query=request.query,
            budget_usd=request.budget_limit,
            thread_id=thread_id,
        )
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"


@app.post("/agent/stream")
def agent_stream(request: QueryRequest):
    """Stream agent execution step-by-step via Server-Sent Events.

    Events emitted:
      - planning: agent's thought + planned steps
      - executing: each tool call as it starts
      - tool_result: each tool result as it completes
      - reflecting: reflector's decision
      - answer: final answer
      - budget: token/cost summary
      - error: if something goes wrong
    """
    thread_id = request.thread_id or f"s-{uuid.uuid4().hex[:8]}"

    def generate():
        try:
            graph = build_graph()
            initial_state: AgentState = {
                "query": request.query,
                "plan": None,
                "observations": [],
                "reflections": [],
                "iteration": 0,
                "budget": BudgetInfo(max_budget_usd=request.budget_limit),
                "final_answer": None,
                "error": None,
            }
            config = {"configurable": {"thread_id": thread_id, "actor_id": "agentic-system"}}

            for event in graph.stream(initial_state, config=config, stream_mode="updates"):
                for node_name, state_update in event.items():
                    if node_name == "planner" and state_update.get("plan"):
                        plan = state_update["plan"]
                        yield _sse_event("planning", {
                            "thought": plan.thought,
                            "steps": [
                                {
                                    "step_id": s.step_id,
                                    "tool": s.tool,
                                    "args": s.args,
                                    "depends_on": s.depends_on,
                                    "reason": s.reason,
                                }
                                for s in plan.steps
                            ],
                        })

                    elif node_name == "executor":
                        observations = state_update.get("observations", [])
                        for obs in observations:
                            yield _sse_event("tool_result", {
                                "step_id": obs.step_id,
                                "tool": obs.tool,
                                "success": obs.success,
                                "result": obs.result,
                                "error": obs.error,
                            })

                    elif node_name == "reflector":
                        if state_update.get("final_answer"):
                            yield _sse_event("answer", {
                                "final_answer": state_update["final_answer"],
                            })
                        else:
                            reflections = state_update.get("reflections", [])
                            if reflections:
                                yield _sse_event("reflecting", {
                                    "feedback": reflections[-1] if reflections else "",
                                })

                        budget = state_update.get("budget")
                        if budget and hasattr(budget, "model_dump"):
                            yield _sse_event("budget", budget.model_dump())

            yield _sse_event("done", {"status": "complete"})

        except Exception as e:
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(generate(), media_type="text/event-stream")


