"""
Google Docs Report Renderer.

Transforms a PulseReport into a Google Docs batchUpdate payload.
"""

from __future__ import annotations

from typing import Any
from datetime import datetime

from src.analysis.models import PulseReport, Theme


def _create_insert_text_request(text: str, style: str = "NORMAL_TEXT") -> list[dict[str, Any]]:
    """Create requests to insert text with a specific named style."""
    requests: list[dict[str, Any]] = [
        {
            "insertText": {
                "endOfSegmentLocation": {"segmentId": ""},
                "text": text,
            }
        }
    ]
    # We could theoretically add styling requests here if we tracked indices,
    # but for simplicity, we rely on basic insertText. Google Docs will use the
    # surrounding style. To apply specific styles, we'd need index tracking,
    # but the simplest way to get styled text at the end of a doc is just inserting text.
    # Actually, let's keep it simple and just insert text.
    return requests


def _format_date(date_obj: datetime | None) -> str:
    """Format a datetime object nicely."""
    if not date_obj:
        return "Unknown Date"
    return date_obj.strftime("%Y-%m-%d")


def render_docs_payload(report: PulseReport) -> list[dict[str, Any]]:
    """
    Render a PulseReport into a Google Docs batchUpdate requests list.

    The requests are designed to append content to the end of a Google Doc.
    """
    requests: list[dict[str, Any]] = []

    # 1. Section Heading
    date_range = f"{_format_date(report.review_window_start)} to {_format_date(report.review_window_end)}"
    heading_text = f"{report.display_name or report.product} — Weekly Review Pulse — W{report.iso_week} ({date_range})\n"
    
    # Insert heading
    requests.extend(_create_insert_text_request(heading_text))

    # 2. Themes and Quotes
    if not report.themes:
        requests.extend(_create_insert_text_request("No significant themes discovered this week.\n"))
    else:
        requests.extend(_create_insert_text_request("\nTOP THEMES:\n"))
        for i, theme in enumerate(report.themes, 1):
            theme_text = f"{i}. {theme.name} ({theme.review_count} reviews)\n   {theme.description}\n"
            requests.extend(_create_insert_text_request(theme_text))

        requests.extend(_create_insert_text_request("\nREAL USER QUOTES:\n"))
        for theme in report.themes:
            valid_quotes = theme.validated_quotes
            if valid_quotes:
                requests.extend(_create_insert_text_request(f"\n{theme.name}:\n"))
                for quote in valid_quotes:
                    attribution = f"[{quote.rating}⭐ | {quote.store} | {_format_date(quote.date)}]"
                    requests.extend(_create_insert_text_request(f'"{quote.text}" - {attribution}\n'))

        # 3. Action Ideas
        has_actions = any(theme.actions for theme in report.themes)
        if has_actions:
            requests.extend(_create_insert_text_request("\nACTION IDEAS:\n"))
            for theme in report.themes:
                for action in theme.actions:
                    action_text = f"• {action.title}: {action.details} (Related to: {theme.name})\n"
                    requests.extend(_create_insert_text_request(action_text))

    # 4. Metadata Block
    metadata_text = (
        f"\nAbout This Pulse:\n"
        f"- Analyzed {report.stats.total_reviews} reviews "
        f"({report.stats.appstore_reviews} App Store, {report.stats.playstore_reviews} Play Store)\n"
        f"- Found {report.stats.clusters_found} clusters\n"
        f"- Anchor ID: {report.section_anchor}\n"
        f"--- \n"
    )
    requests.extend(_create_insert_text_request(metadata_text))

    return requests
