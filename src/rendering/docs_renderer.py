"""
Google Docs Report Renderer.

Transforms a PulseReport into an array of styled text blocks.
"""

from __future__ import annotations

from typing import Any
from datetime import datetime

from src.analysis.models import PulseReport


def _create_block(text: str, bold: bool = False) -> dict[str, Any]:
    """Create a styled text block."""
    return {"text": text, "bold": bold}


def _format_date(date_obj: datetime | None) -> str:
    """Format a datetime object nicely."""
    if not date_obj:
        return "Unknown Date"
    return date_obj.strftime("%Y-%m-%d")


def render_docs_payload(report: PulseReport) -> list[dict[str, Any]]:
    """
    Render a PulseReport into an array of text blocks with basic styling.
    """
    blocks: list[dict[str, Any]] = []

    # 1. Section Heading
    date_range = f"{_format_date(report.review_window_start)} to {_format_date(report.review_window_end)}"
    heading_text = f"{report.display_name or report.product} — Weekly Review Pulse — W{report.iso_week} ({date_range})\n"
    
    # Insert heading
    blocks.append(_create_block(heading_text, bold=True))

    # 2. Themes and Quotes
    if not report.themes:
        blocks.append(_create_block("No significant themes discovered this week.\n", bold=False))
    else:
        blocks.append(_create_block("\nTOP THEMES:\n", bold=True))
        for i, theme in enumerate(report.themes, 1):
            theme_text = f"{i}. {theme.name} ({theme.review_count} reviews)\n   {theme.description}\n"
            blocks.append(_create_block(theme_text, bold=False))

        blocks.append(_create_block("\nREAL USER QUOTES:\n", bold=True))
        for theme in report.themes:
            valid_quotes = theme.validated_quotes
            if valid_quotes:
                blocks.append(_create_block(f"\n{theme.name}:\n", bold=True))
                for quote in valid_quotes:
                    attribution = f"[{quote.rating}⭐ | {quote.store} | {_format_date(quote.date)}]"
                    blocks.append(_create_block(f'"{quote.text}" - {attribution}\n', bold=False))

        # 3. Action Ideas
        has_actions = any(theme.actions for theme in report.themes)
        if has_actions:
            blocks.append(_create_block("\nACTION IDEAS:\n", bold=True))
            for theme in report.themes:
                for action in theme.actions:
                    action_text = f"• {action.title}: {action.details} (Related to: {theme.name})\n"
                    blocks.append(_create_block(action_text, bold=False))

    # 4. Metadata Block
    metadata_text = (
        f"\nAbout This Pulse:\n"
        f"- Analyzed {report.stats.total_reviews} reviews "
        f"({report.stats.appstore_reviews} App Store, {report.stats.playstore_reviews} Play Store)\n"
        f"- Found {report.stats.clusters_found} clusters\n"
        f"- Anchor ID: {report.section_anchor}\n"
        f"--- \n"
    )
    blocks.append(_create_block(metadata_text, bold=False))

    return blocks
