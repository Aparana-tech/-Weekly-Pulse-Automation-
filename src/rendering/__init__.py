"""
Rendering Layer.

Transforms structured PulseReports into delivery payloads (Google Docs batchUpdate,
and Email HTML/text).
"""

from __future__ import annotations

from typing import Any

from src.analysis.models import PulseReport
from src.rendering.docs_renderer import render_docs_payload
from src.rendering.email_renderer import render_email_payload


def render_all(report: PulseReport, doc_id: str = "default_doc_id") -> dict[str, Any]:
    """
    Render a PulseReport into all necessary delivery payloads.

    Args:
        report: The PulseReport to render.
        doc_id: The ID of the target Google Doc (used for deep linking).

    Returns:
        dict containing:
        - docs_payload: list of Google Docs batchUpdate requests.
        - email_content: dict with subject, text_body, and html_body.
    """
    docs_payload = render_docs_payload(report)
    email_content = render_email_payload(report, doc_id=doc_id)

    return {
        "docs_payload": docs_payload,
        "email_content": email_content,
    }

__all__ = ["render_docs_payload", "render_email_payload", "render_all"]
