"""
Cost Tracker Module.

Tracks token usage and estimates USD costs for LLM and Embedding API calls.
Enforces budget cutoffs to prevent runaway spend.
"""

from __future__ import annotations

import structlog

from src.config.settings import Settings
from src.state.models import LLMTokens

logger = structlog.get_logger(__name__)

# Prices per 1000 tokens (USD)
PRICING = {
    "text-embedding-3-small": {
        "input": 0.00002,
        "output": 0.0,
    },
    "gpt-4o-mini": {
        "input": 0.00015,
        "output": 0.00060,
    },
    "gpt-4o": {
        "input": 0.0025,
        "output": 0.0100,
    },
    "llama": {
        "input": 0.0,
        "output": 0.0,
    },
    "all-MiniLM": {
        "input": 0.0,
        "output": 0.0,
    }
}


class BudgetExceededError(Exception):
    """Raised when the cost or token budget is exceeded."""
    pass


class CostTracker:
    """Tracks token usage and enforces budgets."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.total_tokens = LLMTokens()
        
    def _get_pricing(self, model: str) -> dict[str, float]:
        """Get pricing for a model, defaulting to gpt-4o-mini if unknown."""
        # Fallback to gpt-4o-mini if exact model not found
        default = PRICING["gpt-4o-mini"]
        for known_model, prices in PRICING.items():
            if known_model in model:
                return prices
        return default

    def add_usage(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Record usage for an API call and return the estimated cost for this call.
        Raises BudgetExceededError if the total tokens exceed the max allowed.
        """
        # Calculate cost
        pricing = self._get_pricing(model)
        cost_usd = (input_tokens / 1000.0 * pricing["input"]) + (output_tokens / 1000.0 * pricing["output"])
        
        # Update totals
        self.total_tokens.input += input_tokens
        self.total_tokens.output += output_tokens
        self.total_tokens.estimated_cost_usd += cost_usd
        
        # Check token budget
        if self.total_tokens.total > self.settings.max_tokens_per_run:
            logger.error(
                "token_budget_exceeded",
                total=self.total_tokens.total,
                max=self.settings.max_tokens_per_run
            )
            raise BudgetExceededError(f"Token budget exceeded: {self.total_tokens.total} > {self.settings.max_tokens_per_run}")
            
        # Check optional cost threshold (warning only)
        # We don't raise an error here because the token budget is the hard limit,
        # but we could optionally raise an error if cost threshold is also a hard limit.
        if self.total_tokens.estimated_cost_usd > self.settings.cost_alert_threshold_usd:
            logger.warning(
                "cost_threshold_exceeded",
                cost_usd=self.total_tokens.estimated_cost_usd,
                threshold=self.settings.cost_alert_threshold_usd
            )
            
        return cost_usd

    def get_totals(self) -> LLMTokens:
        """Return the running totals."""
        return self.total_tokens

    def log_summary(self) -> None:
        """Log a summary of the total usage and cost."""
        logger.info(
            "cost_tracker_summary",
            input_tokens=self.total_tokens.input,
            output_tokens=self.total_tokens.output,
            total_tokens=self.total_tokens.total,
            cost_usd=round(self.total_tokens.estimated_cost_usd, 4)
        )
