"""Observability — structured tracing, latency tracking, metrics collection.

Tracks every agent run with:
- Request ID for end-to-end tracing
- Per-node latency (planner, executor, reflector)
- Tool call durations
- Token usage per call
- Error rates
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("agent.observability")


@dataclass
class Span:
    """A single timed operation within a trace."""
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)
    error: str | None = None

    def start(self):
        self.start_time = time.time()
        return self

    def end(self, metadata: dict | None = None, error: str | None = None):
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        if metadata:
            self.metadata.update(metadata)
        self.error = error
        return self

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "error": self.error,
        }


@dataclass
class Trace:
    """A full agent execution trace."""
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    query: str = ""
    thread_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    total_duration_ms: float = 0.0
    spans: list[Span] = field(default_factory=list)
    iterations: int = 0
    tools_called: list[str] = field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    success: bool = True
    error: str | None = None

    def start(self, query: str, thread_id: str):
        self.query = query
        self.thread_id = thread_id
        self.start_time = time.time()
        logger.info(f"[TRACE:{self.request_id}] START query='{query[:80]}' thread={thread_id}")
        return self

    def add_span(self, span: Span):
        self.spans.append(span)
        logger.info(
            f"[TRACE:{self.request_id}] {span.name} "
            f"duration={span.duration_ms}ms "
            f"{'ERROR: ' + span.error if span.error else 'OK'}"
        )

    def end(self, budget: dict | None = None, error: str | None = None):
        self.end_time = time.time()
        self.total_duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        if budget:
            self.total_tokens = budget.get("total_input_tokens", 0) + budget.get("total_output_tokens", 0)
            self.total_cost_usd = budget.get("total_cost_usd", 0)
        if error:
            self.success = False
            self.error = error
        logger.info(
            f"[TRACE:{self.request_id}] END "
            f"duration={self.total_duration_ms}ms "
            f"iterations={self.iterations} "
            f"tools={self.tools_called} "
            f"tokens={self.total_tokens} "
            f"cost=${self.total_cost_usd:.4f} "
            f"success={self.success}"
        )
        return self

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "query": self.query[:100],
            "thread_id": self.thread_id,
            "total_duration_ms": self.total_duration_ms,
            "iterations": self.iterations,
            "tools_called": self.tools_called,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "success": self.success,
            "error": self.error,
            "spans": [s.to_dict() for s in self.spans],
        }


# ── Metrics store (in-memory, for /metrics endpoint) ───────────────────

class MetricsStore:
    """Collects aggregate metrics across all requests."""

    def __init__(self):
        self.total_requests = 0
        self.total_errors = 0
        self.total_tokens = 0
        self.total_cost_usd = 0.0
        self.total_duration_ms = 0.0
        self.tool_call_counts: dict[str, int] = {}
        self.recent_traces: list[dict] = []  # Last 50 traces

    def record(self, trace: Trace):
        self.total_requests += 1
        if not trace.success:
            self.total_errors += 1
        self.total_tokens += trace.total_tokens
        self.total_cost_usd += trace.total_cost_usd
        self.total_duration_ms += trace.total_duration_ms
        for tool in trace.tools_called:
            self.tool_call_counts[tool] = self.tool_call_counts.get(tool, 0) + 1
        self.recent_traces.append(trace.to_dict())
        if len(self.recent_traces) > 50:
            self.recent_traces.pop(0)

    def get_summary(self) -> dict:
        avg_duration = (self.total_duration_ms / self.total_requests) if self.total_requests > 0 else 0
        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": round(self.total_errors / max(self.total_requests, 1), 4),
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "avg_duration_ms": round(avg_duration, 2),
            "tool_call_counts": self.tool_call_counts,
        }


# Global metrics store
metrics = MetricsStore()
