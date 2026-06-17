"""
Delivery Layer.

Orchestrates the dispatch of rendered PulseReports to external systems
like Google Docs and Gmail via MCP.
"""

from __future__ import annotations

import logging
from typing import Any

from src.analysis.models import PulseReport
from src.config.settings import Settings
from src.delivery.docs_delivery import append_section_to_doc, check_section_exists
from src.delivery.email_delivery import deliver_email
from src.delivery.mcp_client import MCPClientManager

logger = logging.getLogger(__name__)


async def deliver_pulse(
    report: PulseReport,
    docs_payload: list[dict[str, Any]],
    email_content: dict[str, str],
    doc_id: str,
    email_recipients: list[str],
    settings: Settings,
    client_manager: MCPClientManager,
) -> dict[str, str]:
    """
    Deliver the generated payloads via MCP.

    Args:
        report: The PulseReport instance.
        docs_payload: Google Docs batchUpdate payload.
        email_content: Email payload.
        doc_id: Target Google Doc ID.
        email_recipients: List of target emails.
        settings: Global Settings.
        client_manager: Manager for MCP connections.

    Returns:
        dict containing delivery status strings.
    """
    results = {}
    anchor = report.section_anchor

    logger.info(f"Starting delivery for anchor '{anchor}'")

    # 1. Google Docs Delivery
    try:
        async with client_manager.connect("google-docs") as session:
            # Idempotency check
            exists = await check_section_exists(session, doc_id, anchor)
            if exists:
                results["docs_delivery"] = f"Skipped: Section '{anchor}' already exists."
            else:
                success = await append_section_to_doc(session, doc_id, docs_payload)
                results["docs_delivery"] = "Success" if success else "Failed"
    except Exception as e:
        logger.error(f"Google Docs delivery failed: {e}")
        results["docs_delivery"] = f"Error: {e}"

    # 2. Email Delivery
    if settings.email_mode == "none":
        results["email_delivery"] = "Skipped: Email mode is 'none'"
    else:
        try:
            async with client_manager.connect("gmail") as session:
                mode = settings.email_mode
                msg_id = await deliver_email(
                    session=session,
                    email_content=email_content,
                    recipients=email_recipients,
                    email_mode=mode,
                )
                results["email_delivery"] = f"Success ({mode} ID: {msg_id})"
        except Exception as e:
            logger.error(f"Email delivery failed: {e}")
            results["email_delivery"] = f"Error: {e}"

    return results

__all__ = ["deliver_pulse", "MCPClientManager"]
