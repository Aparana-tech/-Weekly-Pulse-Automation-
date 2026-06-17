"""
Tests for Email Renderer.
"""

from __future__ import annotations

import datetime

from src.analysis.models import PulseReport, RunStats, Theme
from src.rendering.email_renderer import render_email_payload


def create_dummy_report() -> PulseReport:
    """Create a dummy report for testing."""
    return PulseReport(
        product="test_app",
        display_name="Test App",
        iso_year=2026,
        iso_week=23,
        themes=[
            Theme(
                name="Bugs",
                description="Lots of bugs.",
                quotes=[],
                actions=[],
                review_count=10,
                cluster_label=1,
            )
        ],
        stats=RunStats(
            total_reviews=100,
            clusters_found=1,
        )
    )


def test_render_email_payload() -> None:
    """Test email payload rendering."""
    report = create_dummy_report()
    payload = render_email_payload(report, doc_id="12345")

    assert payload["subject"] == "📊 Test App Review Pulse — Week 23"
    
    text_body = payload["text_body"]
    assert "Review Pulse for Test App (Week 23, 2026)" in text_body
    assert "Top Themes:" in text_body
    assert "• Bugs: Lots of bugs." in text_body
    assert "100 reviews analyzed" in text_body
    assert "1 clusters found" in text_body
    assert "https://docs.google.com/document/d/12345/edit#heading=h.test_app-2026-W23" in text_body

    html_body = payload["html_body"]
    assert "<html>" in html_body
    assert "<h2>📊 Review Pulse for Test App (Week 23, 2026)</h2>" in html_body
    assert "<li><strong>Bugs</strong>: Lots of bugs.</li>" in html_body
    assert "100 reviews analyzed" in html_body
    assert "1 clusters found" in html_body
    assert 'href="https://docs.google.com/document/d/12345/edit#heading=h.test_app-2026-W23"' in html_body
