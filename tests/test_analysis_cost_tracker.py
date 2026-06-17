"""
Tests for Cost Tracker.
"""

import pytest

from src.analysis.cost_tracker import BudgetExceededError, CostTracker
from src.config.settings import Settings


def test_cost_tracker_initialization() -> None:
    settings = Settings()
    tracker = CostTracker(settings)
    assert tracker.total_tokens.total == 0
    assert tracker.total_tokens.estimated_cost_usd == 0.0


def test_cost_tracker_pricing() -> None:
    settings = Settings()
    tracker = CostTracker(settings)
    
    # 1000 input tokens of gpt-4o-mini = $0.00015
    cost = tracker.add_usage("gpt-4o-mini", 1000, 0)
    assert cost == 0.00015
    assert tracker.total_tokens.estimated_cost_usd == 0.00015
    assert tracker.total_tokens.input == 1000
    
    # 1000 output tokens of gpt-4o-mini = $0.00060
    cost = tracker.add_usage("gpt-4o-mini", 0, 1000)
    assert cost == pytest.approx(0.00060)
    assert tracker.total_tokens.estimated_cost_usd == pytest.approx(0.00075)
    assert tracker.total_tokens.total == 2000


def test_cost_tracker_budget_enforcement() -> None:
    settings = Settings(max_tokens_per_run=5000)
    tracker = CostTracker(settings)
    
    # Under budget
    tracker.add_usage("gpt-4o-mini", 3000, 1000)
    assert tracker.total_tokens.total == 4000
    
    # Exceeds budget
    with pytest.raises(BudgetExceededError):
        tracker.add_usage("gpt-4o-mini", 1001, 0)
        
    # Budget is exceeded but totals were still updated
    assert tracker.total_tokens.total == 5001
