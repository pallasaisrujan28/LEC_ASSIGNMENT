"""FastAPI application — POST /agent/query + POST /agent/stream endpoints."""

import json
import logging
import os
import sys
import uuid

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agent.api")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agent.core.graph import run_agent, build_graph
from src.agent.core.state import AgentState, BudgetInfo
from langchain_core.messages import HumanMessage, AIMessage

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
        from src.agent.core.guardrails import validate_input, apply_bedrock_guardrail
        query = validate_input(request.query)

        # Check input with Bedrock guardrail
        _, blocked = apply_bedrock_guardrail(query, "INPUT")
        if blocked:
            return QueryResponse(
                query=query,
                final_answer="Your request was blocked by our safety filters. Please rephrase your question.",
            )

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
            # Check input with Bedrock guardrail
            from src.agent.core.guardrails import apply_bedrock_guardrail
            _, blocked = apply_bedrock_guardrail(request.query, "INPUT")
            if blocked:
                yield _sse_event("answer", {"final_answer": "Your request was blocked by our safety filters. Please rephrase your question."})
                yield _sse_event("done", {"status": "complete"})
                return

            graph = build_graph()
            config = {"configurable": {"thread_id": thread_id, "actor_id": "agentic-system"}}

            # Load existing messages from checkpoint if this thread has history
            existing_messages = []
            try:
                existing = graph.get_state(config)
                if existing and existing.values and existing.values.get("messages"):
                    existing_messages = list(existing.values["messages"])
                    logger.info(f"[STREAM] Found {len(existing_messages)} existing messages for thread {thread_id}")
            except Exception as e:
                logger.warning(f"[STREAM] Could not load existing state: {e}")

            # Build state with accumulated messages
            all_messages = existing_messages + [HumanMessage(content=request.query)]

            initial_state: AgentState = {
                "query": request.query,
                "messages": all_messages,
                "plan": None,
                "observations": [],
                "reflections": [],
                "iteration": 0,
                "budget": BudgetInfo(max_budget_usd=request.budget_limit),
                "final_answer": None,
                "error": None,
            }

            logger.info(f"[STREAM] Starting stream for query: {request.query[:100]}, thread: {thread_id}, messages: {len(all_messages)}")

            last_answer = None
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
                            # Apply output guardrail on final answer
                            answer = state_update["final_answer"]
                            checked_answer, was_blocked = apply_bedrock_guardrail(answer, "OUTPUT")
                            last_answer = checked_answer if not was_blocked else answer
                            yield _sse_event("answer", {
                                "final_answer": last_answer,
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

            # Save AI message to checkpoint for conversation history
            if last_answer:
                try:
                    graph.update_state(config, {"messages": [AIMessage(content=last_answer)]})
                except Exception:
                    pass

            yield _sse_event("done", {"status": "complete"})

        except Exception as e:
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


