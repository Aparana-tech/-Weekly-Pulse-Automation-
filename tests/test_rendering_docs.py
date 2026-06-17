"""
Tests for Docs Renderer.
"""

from __future__ import annotations

import datetime

from src.analysis.models import ActionIdea, PulseReport, Quote, RunStats, Theme
from src.rendering.docs_renderer import render_docs_payload


def create_dummy_report() -> PulseReport:
    """Create a dummy report for testing."""
    dummy_date = datetime.datetime.now(datetime.UTC)
    
    return PulseReport(
        product="test_app",
        display_name="Test App",
        iso_year=2026,
        iso_week=23,
        generated_at=dummy_date,
        review_window_start=dummy_date,
        review_window_end=dummy_date,
        themes=[
            Theme(
                name="Bugs",
                description="Lots of bugs.",
                quotes=[
                    Quote(
                        text="It crashed!",
                        review_id="1",
                        rating=1,
                        store="appstore",
                        date=dummy_date,
                        validated=True,
                    ),
                    Quote(
                        text="Unvalidated quote",
                        review_id="2",
                        rating=2,
                        store="appstore",
                        date=dummy_date,
                        validated=False,
                    )
                ],
                actions=[
                    ActionIdea(title="Fix Bugs", details="Fix the bugs please.", related_theme="Bugs")
                ],
                review_count=10,
                cluster_label=1,
            )
        ],
        stats=RunStats(
            total_reviews=100,
            appstore_reviews=60,
            playstore_reviews=40,
            clusters_found=1,
        )
    )


def test_render_docs_payload_basic() -> None:
    """Test that docs payload generates correctly for a basic report."""
    report = create_dummy_report()
    requests = render_docs_payload(report)

    assert len(requests) > 0
    # Check that it uses insertText with endOfSegmentLocation
    assert "insertText" in requests[0]
    assert "endOfSegmentLocation" in requests[0]["insertText"]

    # Combine all text to check contents easily
    full_text = "".join(req["insertText"]["text"] for req in requests)

    # Check sections
    assert "Test App — Weekly Review Pulse — W23" in full_text
    assert "Top Themes:" in full_text
    assert "1. Bugs (10 reviews)" in full_text
    assert "Lots of bugs." in full_text
    assert "Real User Quotes:" in full_text
    
    # Check that ONLY validated quotes are included
    assert '"It crashed!"' in full_text
    assert "Unvalidated quote" not in full_text
    
    # Check actions
    assert "Action Ideas:" in full_text
    assert "Fix Bugs" in full_text

    # Check metadata block
    assert "About This Pulse:" in full_text
    assert "Analyzed 100 reviews (60 App Store, 40 Play Store)" in full_text
    assert "Found 1 clusters" in full_text
    assert "Anchor ID: test_app-2026-W23" in full_text


def test_render_docs_payload_empty_themes() -> None:
    """Test docs payload generation when there are no themes."""
    report = create_dummy_report()
    report.themes = []
    
    requests = render_docs_payload(report)
    full_text = "".join(req["insertText"]["text"] for req in requests)
    
    assert "No significant themes discovered this week." in full_text
    assert "Top Themes:" not in full_text
    assert "Real User Quotes:" not in full_text
    assert "Action Ideas:" not in full_text
