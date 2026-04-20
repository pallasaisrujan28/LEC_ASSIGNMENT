"""Token + cost tracking with hard budget cap."""

import os

from src.agent.core.state import BudgetInfo

# Claude Sonnet 4 pricing (per 1M tokens)
INPUT_COST_PER_1M = 3.00
OUTPUT_COST_PER_1M = 15.00


class BudgetExceededError(Exception):
    """Raised when the budget cap is hit."""

    pass


class BudgetTracker:
    """Tracks token usage and cost across LLM calls."""

    def __init__(self, max_budget_usd: float | None = None):
        self.max_budget_usd = max_budget_usd or float(
            os.environ.get("BUDGET_CAP_USD", "20.0")
        )
        self.info = BudgetInfo(max_budget_usd=self.max_budget_usd)

    def check_budget(self):
        """Raise if remaining budget is insufficient for another call."""
        if self.info.total_cost_usd >= self.max_budget_usd:
            raise BudgetExceededError(
                f"Budget exceeded: ${self.info.total_cost_usd:.4f} / ${self.max_budget_usd}"
            )

    def record_usage(self, input_tokens: int, output_tokens: int):
        """Record token usage from an LLM call."""
        self.info.total_input_tokens += input_tokens
        self.info.total_output_tokens += output_tokens
        self.info.calls += 1

        input_cost = (input_tokens / 1_000_000) * INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
        self.info.total_cost_usd += input_cost + output_cost

    def get_summary(self) -> dict:
        """Return a summary of usage."""
        return {
            "total_input_tokens": self.info.total_input_tokens,
            "total_output_tokens": self.info.total_output_tokens,
            "total_cost_usd": round(self.info.total_cost_usd, 6),
            "max_budget_usd": self.max_budget_usd,
            "remaining_usd": round(
                self.max_budget_usd - self.info.total_cost_usd, 6
            ),
            "llm_calls": self.info.calls,
        }
