# Technical Documentation

## Problem Statement

Build a production grade AI agent that orchestrates 5 or more tools to answer multi step queries reliably. The agent must demonstrate explicit planning, parallel execution of independent tool calls, token and cost tracking with a hard budget cap, graceful failure recovery, infinite loop prevention, and measurable evaluation with graded success criteria.

## Assumptions

1. The agent operates in a stateless request/response model where each query triggers a fresh planning cycle, but conversation memory persists across turns via AgentCore Memory checkpointing.
2. Have setup infrastructure on AWS and for this project using Claude Sonnet 4.6 via AWS Bedrock
4. Tool responses are treated as untrusted input. The reflector synthesises answers from tool results rather than passing raw output to the user.
5. According to the requirements I have created a hard budget limit of 20$ which when hit will notify the user.

## Tool Definitions

I have built 5 tool functions (covering the 5 required categories) using the LangChain `@tool` decorator pattern:

**web_search** uses the Tavily API to search the internet for real time data, news, and current events. I have swapped to Tavily over DuckDuckGo because DuckDuckGo was causing rate limiting requests even after implementing a proxy and timeout retries during development.

**calculator** uses sympy to evaluate mathematical expressions. It handles arithmetic, algebra, trigonometry, logarithms, and percentage calculations. During the development the model was doing the calculations by itself , Hence planner is explicitly instructed through prompt to never do math itself and always delegate to this tool.

**wiki_summary and wiki_search(Chose this as my 5th tool)** uses the wikipedia-api library to retrieve Wikipedia article summaries and search for article titles. wiki_summary takes a topic name and returns a concise summary. wiki_search finds relevant article titles for a given query. These are used for factual, encyclopedic knowledge.

**knowledge_base_lookup** uses the Bedrock Agent Runtime `Retrieve` API to search a pre built knowledge base backed by S3 Vectors. The knowledge base is created with a Titan Embed Text v2 embedding model (1024 dimensions) and an S3 Vector bucket as the vector store. Documents are ingested from an S3 bucket and the pipeline triggers a sync on every deployment. This tool is used for structured, indexed information about specific topics.

**document_qa** takes a question and user provided document text, chunks the text into paragraphs, scores each paragraph by keyword overlap with the question, and returns the most relevant passages. The reflector (main LLM) then generates the final answer from these passages.

## Agent Orchestration System

### Architecture

I have implemented a Plan and Execute architecture using LangGraph ([LangGraph docs](https://langchain-ai.github.io/langgraph/)). The graph has three nodes wired in a cycle:

**Planner** receives the user query and conversation history, then produces a structured JSON plan using `with_structured_output`. Each plan contains a thought (reasoning), and a list of steps where each step specifies a tool name, arguments, and dependency declarations. The planner uses the v2 improved prompt loaded from `src/prompts/v2_improved.txt`.

**Executor** takes the plan and dispatches tool calls. It performs a topological sort on the dependency graph to determine execution order. Steps with no unresolved dependencies are grouped and run in parallel via `asyncio.gather`. Steps that depend on previous results wait until those results are available. Each tool call is retried up to 2 times on failure. The executor produces a list of Observation objects (step_id, tool, success, result, error).

**Reflector** receives the original query, conversation history, plan, and all observations. It uses `with_structured_output` to produce a ReflectionResult containing either a final answer (is_done=True) or feedback for re planning (is_done=False). If the reflector determines more work is needed, the loop returns to the planner with the feedback. After iteration 2, the reflector is forced to produce a final answer regardless.

### The Tool Loop

```
query → planner (LLM call) → executor (tool calls, parallel when independent) → observations → reflector (LLM call) → done? → final answer
                                                                                                                    ↓ no
                                                                                                              back to planner
```

Each iteration through this loop is a minimum of 2 LLM calls (planner + reflector) plus the actual tool executions. The loop terminates when: the reflector produces a final answer, the iteration count reaches 8, or the budget is exhausted.

### Issues Faced and Solutions

**Structured output returning None**: When Bedrock guardrails were applied directly on LLM calls, `with_structured_output` would return None for normal queries because the guardrail response format conflicted with the structured output parser. I solved this by applying Bedrock guardrails at the API level (using the `ApplyGuardrail` API directly on input/output text) rather than embedding them in LLM calls.

**Async/sync executor conflict**: The executor uses `asyncio.gather` for parallel tool execution, but LangGraph's `invoke` (sync) cannot call async nodes. I resolved this by making the executor node synchronous and using `asyncio.run()` internally. When called from the async FastAPI endpoints via `ainvoke`, LangGraph handles the sync to async bridging automatically by running the sync node in a thread pool.

**Planner hallucinating tool names**: The planner would sometimes invent tool names not in the registry. I added a guardrail in `validate_plan()` that checks every step's tool name against a whitelist of valid tools and rejects the plan if any are unknown.

**Calculator not being used for math**: The reflector would sometimes do arithmetic itself instead of requesting a calculator step. I added an explicit negative constraint in the reflector prompt: "NEVER do math or calculations yourself. If a calculation is needed and the calculator tool was not used, request a RE PLAN asking for a calculator step."

## Guardrails, Reliability, and Monitoring

### Guardrails

I have implemented two layers of guardrails:

**Bedrock Managed Guardrails** are configured via Terraform and applied at the API level using the `ApplyGuardrail` API. They include content filtering (hate, insults, sexual, violence, misconduct, prompt Injections), denied topics (illegal activities, self harm), word filters (profanity), and PII handling (email/phone anonymised, credit card/SSN blocked). The guardrail is applied on both input (before the agent runs) and output (after the final answer).

**Custom Python Guardrails** run in the application code. Input validation rejects empty queries and queries exceeding 3000 characters(built to not execute the budget faster). Plan validation prevents plans with more than 8 steps, duplicate tool calls with identical arguments, and unknown tool names. Output sanitisation strips HTML/script tags, internal error traces, and system prompt leaks. A code level grounding check warns if the final answer does not reference any tool results.

### Observability and Monitoring

I have built a custom observability module with Trace, Span, and MetricsStore classes. Each agent run gets a unique trace with spans for planner, executor, and reflector nodes. The MetricsStore collects aggregate statistics (total requests, error rate, total tokens, total cost, average duration, tool call counts) and exposes them via a `/metrics` endpoint. The last 50 traces are available via `/traces`. All nodes emit structured log messages with timing and status information.

LangSmith tracing is enabled for production monitoring. All LLM calls, tool executions, and graph transitions are traced to LangSmith EU endpoint. The project is configured as `LEC-AGENT` with tracing enabled via `LANGCHAIN_TRACING_V2=true`.

## Evaluation

I have set up two evaluation systems:

**DeepEval** (`tests/test_agent_eval.py`) contains 20 multi step queries graded by three metrics using Bedrock as the judge model: AnswerRelevancy (threshold 0.7), ToolCorrectness (threshold 0.5), and GEval Correctness (threshold 0.7).  The test suite also includes 6 guardrail tests, 3 multi turn conversation tests, 2 edge case tests, and 6 tool registration/functionality tests ([DeepEval docs](https://docs.confident-ai.com/docs/getting-started)).

**LangSmith Evaluation** is set up with custom evaluators for answer_not_empty, guardrail_check, tool_usage, cost_check, and multi_step_query_check. Results are available at: https://eu.smith.langchain.com/public/d104bb67-a821-4948-bb9f-96a0a8c98f37/d

## Context Engineering and Conversation Memory

I have implemented conversation memory using AgentCore Memory as the LangGraph checkpointer ([langgraph-checkpoint-aws docs](https://github.com/langchain-ai/langgraph-checkpoint-aws)). The checkpointer persists the full graph state (messages, plan, observations, reflections) per thread, keyed by `actor_id` and `thread_id`.

Both the planner and reflector receive conversation history via a `get_conversation_context()` function that formats previous turns into a readable string. This allows the agent to understand references like "it", "that", and "earlier" in follow up queries.

To prevent context windows from growing unbounded, I have implemented automatic conversation summarisation. After 5 human/AI message pairs, older messages are summarised by the LLM into a compact SystemMessage and the originals are replaced. The 2 most recent pairs are always kept verbatim. This keeps the context window manageable while preserving important information from earlier in the conversation.

## Infinite Loop Prevention and Tool Error Handling

The agent has multiple safeguards against infinite loops:

1. A hard cap of 8 iterations on the planner/executor/reflector cycle.
2. After iteration 2, the reflector is forced to produce a final answer regardless of whether it thinks more work is needed.
3. The budget tracker checks remaining budget before each LLM call and raises a BudgetExceededError if the $20 cap is hit.
4. Plan validation rejects duplicate tool calls with identical arguments, preventing the agent from repeating the same action.

For tool errors, each tool call is retried up to 2 times. If all retries fail, the error is wrapped in an Observation object with `success=False` and passed to the reflector. The reflector is instructed to work with partial information if some tools failed but others succeeded, and only request a re plan if critical information is missing.

## Scaling and Concurrent Request Handling

The backend runs on AWS ECS Fargate with an Application Load Balancer. The container runs uvicorn with 4 workers on port 8080. Auto scaling is configured with two policies:

**Request based scaling** tracks ALB request count per target with a target value of 100. When the average requests per task exceeds 100, ECS scales out. This directly addresses the 100 concurrent request requirement.

**CPU based scaling** tracks ECS service average CPU utilisation with a target of 70%. This catches scenarios where requests are computationally heavy (multiple LLM calls per request).

The service scales from 1 to 10 tasks with a scale out cooldown of 30 seconds and scale in cooldown of 120 seconds.

## Prompt Ablation

I have created two prompt versions stored in `src/prompts/`:

**v1_baseline.txt** is a clean, functional prompt that lists the available tools with their parameter names and provides 4 basic rules: use only needed tools, use calculator for math, declare dependencies, and provide reasons for each step.

**v2_improved.txt** builds on v1 by applying structured prompt engineering techniques:
- Explicit constraint enumeration with 9 detailed rules instead of 4
- Source routing heuristics that guide the planner on when to use wiki_summary (static facts) vs web_search (real time data)
- Parallelism hints that instruct the planner to make separate calls for independent entities so they can run in parallel
- Negative constraints ("NEVER answer math questions directly", "Do NOT use all tools") to prevent common failure modes
- Stronger calculator enforcement requiring the calculator for any numerical computation

The v2 prompt is loaded from file and used by the planner in production. The key improvement is that v2 reduces unnecessary tool calls and improves tool selection accuracy by giving the planner explicit decision criteria rather than leaving it to infer the right tool from descriptions alone.

## Frontend

The frontend is a Next.js application with a static export deployed to S3 and served via CloudFront. It connects to the backend via SSE (Server Sent Events) for streaming agent responses. The UI shows the agent's planning steps, tool results (collapsible), and the final answer in real time as the agent works through the query.

## Infrastructure and CI/CD

All infrastructure is managed via Terraform with state stored in S3. The CI/CD pipeline runs on GitHub Actions with three parallel jobs after infrastructure: backend (Docker build, ECR push, ECS task definition registration, service update), frontend (Next.js build, S3 sync, CloudFront invalidation), and knowledge base sync (triggers Bedrock ingestion job). GitHub Actions authenticates to AWS via OIDC federation.

## Improvements

**Convert tools to MCP**: The current tools use the LangChain `@tool` decorator which couples them to this specific agent. Converting to Model Context Protocol (MCP) servers would make each tool independently deployable and reusable across different agents if we want to scale to multiple agents in future.

**Tool specific planning rules**: The agent planning loop currently treats all tools uniformly. Defining per tool constraints (e.g., "web_search should never be called more than 3 times per plan", "calculator must always follow a data retrieval step") would reduce wasted tool calls and improve plan quality.

**Cold start latency**: The biggest throughput bottleneck is the initial LLM call to the planner. Each planning call takes 2 to 5 seconds depending on query complexity. For high throughput scenarios, pre warming the Bedrock connection and implementing plan caching for common query patterns would significantly reduce p50 latency.

**Multi file document injection and querying**: The current document Q&A tool supports a single PDF per session. Extending this to accept multiple files, maintain a per session document index, and allow the user to query across all uploaded documents simultaneously would make the tool significantly more useful for research and analysis workflows.

**Tool result caching with TTL**: Web search and Wikipedia results for the same query should be cached with a configurable TTL. This would reduce API calls, lower costs, and improve response times for repeated or similar queries.

**Adaptive re planning with error context**: Instead of the reflector simply saying "re plan", it would provide structured feedback about what went wrong and what alternative approach to try. This would reduce the number of wasted re planning iterations.

**Evaluation dashboard**: Build a lightweight dashboard that visualises evaluation results over time, showing success rate trends, common failure patterns, and cost per query distributions. This would make prompt iteration and system improvement data driven.

## AI Usage Note

I have used AI assistance in the following areas:

**Frontend**: I used Claude to build the Next.js frontend components. I provided the styling direction (warm dark theme, specific colour values, UI box dimensions) and Claude generated the React/TypeScript code to match.

**Evaluation tests**: I used AI to build the DeepEval test cases. I provided the input queries and expected outputs, and asked it to create test cases using those scenarios with the appropriate metrics and thresholds.

**Tool implementations**: I used AI to build the tool code. The tools are straightforward API wrappers (Tavily, sympy, wikipedia-api, Bedrock Retrieve), so I had AI generate the initial implementations and then tested each one individually by running multiple automated tests to verify correctness.


All AI generated code was reviewed, tested, and modified as needed. The architectural decisions, prompt engineering, evaluation criteria, and system design were my own.
