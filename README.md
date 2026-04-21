# Production Agentic System

A production grade AI agent that orchestrates 5 tools to answer multi step queries using a Plan and Execute architecture on LangGraph, deployed on AWS ECS Fargate with auto scaling.

## Live URL

**https://d2xw8rvm35dsgi.cloudfront.net**

## Running Locally

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 20+
- AWS credentials configured (for Bedrock, AgentCore Memory, guardrails)
- A `.env` file in the repository root with the required environment variables

### Backend

```bash
cd backend
uv sync
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8080
```

The backend will be available at `http://localhost:8080`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`. For local development, it defaults to connecting to `http://localhost:8080` for the backend.

### Running Tests

```bash
cd backend
uv run python -m pytest tests/test_agent_eval.py -v
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/agent/stream` | POST | SSE streaming endpoint (used by the frontend) |
| `/agent/upload` | POST | Upload a PDF document (max 500KB) for document Q&A |
| `/invocations` | POST | JSON request/response endpoint |
| `/metrics` | GET | Observability metrics |
| `/traces` | GET | Recent execution traces |

## Sample Queries

Try these in the chat interface:

**Multi tool (Wikipedia + Calculator):**
> What is the population of Japan and what is 3% of it?

**Web search + Calculator:**
> Search for the current price of Bitcoin and calculate what 0.5 BTC is worth.

**Parallel Wikipedia lookups + Calculator:**
> What are the populations of France and the UK, and what is the difference?

**Chained calculations:**
> What is 1500 * 12, then take 20% of that, then add 500?

**Web search + Wikipedia:**
> What are the latest AI breakthroughs in 2026, and give me a Wikipedia summary of the Transformer architecture?

**Document Q&A (upload a PDF first using the paperclip icon):**
> What is this document about?
> Who is the target audience?

**Knowledge Base Lookup:**
> What do you know about London Export Corporation?
> Tell me about LEC's history with China trade.

**Conversational (no tools):**
> Hello, how are you?

## Documentation

See [Agentic%20System/docs/technical-documentation.md](Agentic System/docs/technical-documentation.md) for the full technical writeup covering architecture, tools, guardrails, evaluation, prompt ablation, scaling, and AI usage.
