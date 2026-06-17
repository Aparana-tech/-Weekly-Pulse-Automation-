"""
Tests for Rendering Integration.
"""

from __future__ import annotations

import datetime

from src.analysis.models import PulseReport, RunStats
from src.rendering import render_all


def test_render_all() -> None:
    """Test unified rendering function."""
    report = PulseReport(
        product="test_app",
        display_name="Test App",
        iso_year=2026,
        iso_week=23,
        themes=[],
        stats=RunStats()
    )
    
    result = render_all(report, doc_id="abc")
    
    assert "docs_payload" in result
    assert "email_content" in result
    
    assert isinstance(result["docs_payload"], list)
    assert len(result["docs_payload"]) > 0
    
    assert "subject" in result["email_content"]
    assert "text_body" in result["email_content"]
    assert "html_body" in result["email_content"]
    
    assert "abc" in result["email_content"]["text_body"]
