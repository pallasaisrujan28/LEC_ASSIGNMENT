"""FastAPI application — serves the Plan-and-Execute agent.

Endpoints:
  POST /invocations  — AgentCore-compatible invoke (JSON payload)
  POST /agent/stream  — SSE streaming for the frontend
  GET  /health        — Health check
  GET  /ping          — Ping (ALB health check)
  GET  /metrics       — Observability metrics
  GET  /traces        — Recent traces
"""

import json
import logging
import os
import sys
import uuid

from dotenv import load_dotenv
from pathlib import Path

# Load env — try multiple paths
for p in [
    Path(__file__).resolve().parent.parent.parent.parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",
]:
    if p.exists():
        load_dotenv(p)
        break

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agent.api")

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

from src.agent.core.graph import build_graph
from src.agent.core.state import AgentState, BudgetInfo
from src.agent.core.guardrails import (
    validate_input, apply_bedrock_guardrail, sanitize_output, check_grounding,
)
from src.agent.core.memory import maybe_summarize

# ── Document store (session → extracted PDF text) ───────────────────────
# In-memory store keyed by thread_id. Persists for the lifetime of the container.
document_store: dict[str, str] = {}

# ── FastAPI App ─────────────────────────────────────────────────────────

app = FastAPI(title="LEC Agentic System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BUDGET_CAP = float(os.environ.get("BUDGET_CAP_USD", "20.0"))


# ── Shared async agent runner ──────────────────────────────────────────

async def _run_agent_async(query: str, budget_usd: float, thread_id: str) -> dict:
    """Run the agent asynchronously."""
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id, "actor_id": "agentic-system"}}

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

    try:
        existing = await graph.aget_state(config)
        if existing and existing.values and existing.values.get("messages"):
            await graph.aupdate_state(config, {
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
            result = await graph.ainvoke(None, config=config)
        else:
            result = await graph.ainvoke(initial_state, config=config)
    except Exception as e:
        logger.error(f"[AGENT] Error: {e}", exc_info=True)
        result = {**initial_state, "error": str(e)}

    # Save AI response + maybe summarize
    final_answer = result.get("final_answer", "")
    if final_answer and not result.get("error"):
        try:
            await graph.aupdate_state(config, {"messages": [AIMessage(content=final_answer)]})
            current_state = await graph.aget_state(config)
            if current_state and current_state.values.get("messages"):
                summarized = maybe_summarize(current_state.values["messages"])
                if len(summarized) != len(current_state.values["messages"]):
                    await graph.aupdate_state(config, {"messages": summarized})
        except Exception:
            pass

    # Build response
    plan_output = None
    if result.get("plan"):
        plan_output = {
            "thought": result["plan"].thought,
            "steps": [
                {"step_id": s.step_id, "tool": s.tool, "args": s.args,
                 "depends_on": s.depends_on, "reason": s.reason}
                for s in result["plan"].steps
            ],
        }

    observations_output = [
        {"step_id": o.step_id, "tool": o.tool, "success": o.success,
         "result": o.result, "error": o.error}
        for o in result.get("observations", [])
    ]

    raw_answer = result.get("final_answer", "Agent could not produce an answer.")
    clean_answer = sanitize_output(raw_answer)
    clean_answer = check_grounding(clean_answer, result.get("observations", []))

    return {
        "query": query,
        "plan": plan_output,
        "observations": observations_output,
        "final_answer": clean_answer,
        "reflections": result.get("reflections", []),
        "iterations": result.get("iteration", 0),
        "budget": result["budget"].model_dump() if hasattr(result.get("budget"), "model_dump") else {},
        "error": result.get("error"),
    }


# ── Endpoints ───────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/ping")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics_endpoint():
    from src.agent.core.observability import metrics
    return metrics.get_summary()


@app.get("/traces")
async def traces_endpoint():
    from src.agent.core.observability import metrics
    return {"traces": metrics.recent_traces}


MAX_PDF_SIZE = 500 * 1024  # 500 KB


@app.post("/agent/upload")
async def upload_document(file: UploadFile = File(...), thread_id: str = Form(...)):
    """Upload a PDF document (max 500KB) for the session. Extracted text is stored for document_qa."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return JSONResponse({"error": "Only PDF files are accepted."}, status_code=400)

    content = await file.read()
    if len(content) > MAX_PDF_SIZE:
        return JSONResponse({"error": f"File too large ({len(content) // 1024}KB). Maximum is 500KB."}, status_code=400)

    try:
        import fitz  # pymupdf
        doc = fitz.open(stream=content, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        extracted = "\n".join(text_parts).strip()
    except Exception as e:
        return JSONResponse({"error": f"Failed to extract text from PDF: {str(e)}"}, status_code=400)

    if not extracted:
        return JSONResponse({"error": "No text could be extracted from the PDF."}, status_code=400)

    document_store[thread_id] = extracted
    logger.info(f"[UPLOAD] thread={thread_id} file={file.filename} chars={len(extracted)}")

    return JSONResponse({
        "status": "ok",
        "filename": file.filename,
        "chars_extracted": len(extracted),
        "thread_id": thread_id,
    })


@app.post("/invocations")
async def invocations(request: Request):
    """AgentCore-compatible invoke endpoint."""
    payload = await request.json()
    query = payload.get("query", payload.get("prompt", ""))
    thread_id = payload.get("thread_id", payload.get("session_id", f"t-{uuid.uuid4().hex[:8]}"))
    budget_usd = float(payload.get("budget_limit", BUDGET_CAP))

    logger.info(f"[INVOKE] query='{query[:80]}' thread={thread_id}")

    try:
        query = validate_input(query)
    except Exception as e:
        return JSONResponse({"result": str(e), "session_id": thread_id, "error": True})

    _, blocked = apply_bedrock_guardrail(query, "INPUT")
    if blocked:
        return JSONResponse({"result": "Your request was blocked by our safety filters.", "session_id": thread_id, "blocked": True})

    try:
        result = await _run_agent_async(query=query, budget_usd=budget_usd, thread_id=thread_id)
    except Exception as e:
        logger.error(f"[INVOKE] Error: {e}", exc_info=True)
        return JSONResponse({"result": f"Error: {str(e)}", "session_id": thread_id, "error": True})

    final_answer = result.get("final_answer", "")
    if final_answer:
        checked, was_blocked = apply_bedrock_guardrail(final_answer, "OUTPUT")
        if was_blocked:
            final_answer = checked

    response = {"result": final_answer or "I couldn't process your request.", "session_id": thread_id}
    if result.get("plan"):
        response["plan"] = result["plan"]
    if result.get("budget"):
        response["budget"] = result["budget"]
    if result.get("observations"):
        response["observations"] = result["observations"]

    logger.info(f"[INVOKE] Complete, iterations={result.get('iterations', 0)}")
    return JSONResponse(response)


@app.post("/agent/stream")
async def stream_endpoint(request: Request):
    """SSE streaming endpoint for the frontend."""
    body = await request.json()
    query = body.get("query", "")
    thread_id = body.get("thread_id", f"s-{uuid.uuid4().hex[:8]}")
    budget_limit = float(body.get("budget_limit", BUDGET_CAP))

    async def generate():
        try:
            _, blocked = apply_bedrock_guardrail(query, "INPUT")
            if blocked:
                yield f"event: answer\ndata: {json.dumps({'final_answer': 'Your request was blocked by our safety filters.'})}\n\n"
                yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"
                return

            graph = build_graph()
            config = {"configurable": {"thread_id": thread_id, "actor_id": "agentic-system"}}

            existing_messages = []
            try:
                existing = await graph.aget_state(config)
                if existing and existing.values and existing.values.get("messages"):
                    existing_messages = list(existing.values["messages"])
            except Exception:
                pass

            all_messages = existing_messages + [HumanMessage(content=query)]

            initial_state: AgentState = {
                "query": query,
                "messages": all_messages,
                "plan": None,
                "observations": [],
                "reflections": [],
                "iteration": 0,
                "budget": BudgetInfo(max_budget_usd=budget_limit),
                "final_answer": None,
                "error": None,
            }

            last_answer = None
            async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
                for node_name, state_update in event.items():
                    if node_name == "planner" and state_update.get("plan"):
                        plan = state_update["plan"]
                        yield f"event: planning\ndata: {json.dumps({'thought': plan.thought, 'steps': [{'step_id': s.step_id, 'tool': s.tool, 'args': s.args, 'depends_on': s.depends_on, 'reason': s.reason} for s in plan.steps]}, default=str)}\n\n"

                    elif node_name == "executor":
                        for obs in state_update.get("observations", []):
                            yield f"event: tool_result\ndata: {json.dumps({'step_id': obs.step_id, 'tool': obs.tool, 'success': obs.success, 'result': obs.result, 'error': obs.error}, default=str)}\n\n"

                    elif node_name == "reflector":
                        if state_update.get("final_answer"):
                            last_answer = state_update["final_answer"]
                            yield f"event: answer\ndata: {json.dumps({'final_answer': last_answer})}\n\n"
                        elif state_update.get("reflections"):
                            yield f"event: reflecting\ndata: {json.dumps({'feedback': state_update['reflections'][-1]})}\n\n"

                        budget = state_update.get("budget")
                        if budget and hasattr(budget, "model_dump"):
                            yield f"event: budget\ndata: {json.dumps(budget.model_dump())}\n\n"

            if last_answer:
                try:
                    await graph.aupdate_state(config, {"messages": [AIMessage(content=last_answer)]})
                except Exception:
                    pass

            yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"

        except Exception as e:
            logger.error(f"[STREAM] Error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
