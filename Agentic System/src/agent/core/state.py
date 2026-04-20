"""Agent state schema for LangGraph."""

from typing import Any

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class PlanStep(BaseModel):
    """A single step in the agent's plan."""

    step_id: str = Field(description="Unique step identifier, e.g. 'step_1'")
    tool: str = Field(description="Tool name to call")
    args: dict[str, Any] = Field(description="Arguments to pass to the tool")
    depends_on: list[str] = Field(
        default_factory=list,
        description="List of step_ids this step depends on",
    )
    reason: str = Field(description="Why this step is needed")


class Plan(BaseModel):
    """The agent's structured plan."""

    thought: str = Field(description="Agent's reasoning about the query")
    steps: list[PlanStep] = Field(description="Ordered list of steps to execute")


class Observation(BaseModel):
    """Result from executing a tool."""

    step_id: str
    tool: str
    success: bool
    result: Any = None
    error: str | None = None


class BudgetInfo(BaseModel):
    """Token and cost tracking."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    max_budget_usd: float = 20.0
    calls: int = 0


class AgentState(TypedDict):
    """LangGraph state for the Plan-and-Execute agent."""

    query: str
    plan: Plan | None
    observations: list[Observation]
    reflections: list[str]
    iteration: int
    budget: BudgetInfo
    final_answer: str | None
    error: str | None
    _thread_id: str
