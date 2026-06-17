"""
Gmail Delivery Module.

Interacts with the Gmail MCP server to create and send drafts with PulseReports.
"""

from __future__ import annotations

import logging

from mcp import ClientSession

from src.delivery.mcp_client import MCPToolInvoker

logger = logging.getLogger(__name__)


async def deliver_email(
    session: ClientSession,
    email_content: dict[str, str],
    recipients: list[str],
    email_mode: str,
) -> str:
    """
    Create a draft or send an email via the Gmail MCP server.
    
    Args:
        session: Active MCP ClientSession for gmail.
        email_content: dict containing 'subject', 'text_body', and 'html_body'.
        recipients: List of email addresses.
        email_mode: "draft" to create a draft, "send" to send directly.
        
    Returns:
        The draft ID or message ID.
    """
    subject = email_content["subject"]
    html_body = email_content["html_body"]
    
    # We join recipients with commas for standard email headers
    to_header = ", ".join(recipients)
    
    if email_mode == "send":
        logger.info(f"Sending email directly to {len(recipients)} recipients")
        tool_name = "send_email"
    else:
        logger.info(f"Creating email draft for {len(recipients)} recipients")
        tool_name = "create_draft"
        
    result = await MCPToolInvoker.invoke_tool(
        session=session,
        tool_name=tool_name,
        arguments={
            "to": to_header,
            "subject": subject,
            "body": html_body,
        },
        timeout=30.0,
    )
    
    # Parse the result to return the ID. Depending on the MCP server implementation,
    # the ID will be in the response text. For simplicity, we just extract the full text.
    result_text = ""
    if hasattr(result, "content") and result.content:
        result_text = "".join(getattr(b, "text", "") for b in result.content)
        
    return result_text
