# Production Agentic System

## Problem Statement

Build a production-grade AI agent that breaks down complex, multi-step user queries into a structured plan, executes the plan by orchestrating multiple tools (sequentially or in parallel), reflects on the results, and produces a final answer — all while tracking token usage, enforcing cost budgets, and recovering gracefully from failures.

## What We Understood

The core challenge is not "can an LLM call a tool" — it's building the orchestration layer that makes it reliable, observable, and cost-aware:

- The agent must think before it acts — an explicit planning step that produces a visible, structured plan before any tool is called
- Tools must be composable — the agent decides which tools to use, in what order, and which can run in parallel
- The system must know when to stop — budget caps, loop prevention, and graceful termination when things go wrong
- Failures are expected — a tool timing out or returning garbage shouldn't crash the agent; it should adapt
- Quality must be measurable — not "it seems to work" but graded evaluation with real success-rate numbers

## Architecture

Plan-and-Execute pattern on LangGraph with 5 MCP tool servers, AWS Bedrock AgentCore Memory, and FastAPI.

## Stack

| Component | Choice |
|-----------|--------|
| Agent Framework | LangGraph (Plan-and-Execute) |
| Memory | AWS Bedrock AgentCore Memory |
| Tools | MCP servers via `langchain-mcp-adapters` |
| LLM | AWS Bedrock |
| API | FastAPI |
| Package Manager | uv |
