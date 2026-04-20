"""FastAPI application — POST /agent/query endpoint."""

import os
import sys

from dotenv import load_dotenv

# Load env vars from parent .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.agent.core.graph import run_agent

app = FastAPI(
    title="Production Agentic System",
    description="Plan-and-Execute agent with 5+ tools",
    version="0.1.0",
)


class QueryRequest(BaseModel):
    query: str
    budget_limit: float = Field(default=20.0, description="Max budget in USD")
    thread_id: str = Field(default="default", description="Session thread ID")


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
        result = run_agent(
            query=request.query,
            budget_usd=request.budget_limit,
            thread_id=request.thread_id,
        )
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
