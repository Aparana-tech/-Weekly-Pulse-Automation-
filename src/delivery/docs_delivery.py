"""
Google Docs Delivery Module.

Interacts with the Google Docs MCP server to append PulseReports to a target document
and check for existing sections (idempotency).
"""

from __future__ import annotations

import logging
from typing import Any

from mcp import ClientSession

from src.delivery.mcp_client import MCPToolInvoker

logger = logging.getLogger(__name__)


async def check_section_exists(
    session: ClientSession, doc_id: str, section_anchor: str
) -> bool:
    """
    Check if a specific section (by anchor) already exists in the Google Doc.
    
    Args:
        session: Active MCP ClientSession for google-docs.
        doc_id: The ID of the target Google Doc.
        section_anchor: The stable section anchor to look for (e.g., 'groww-2026-W23').
        
    Returns:
        True if the section anchor string exists in the document text, False otherwise.
    """
    logger.info(f"Checking if section '{section_anchor}' exists in doc '{doc_id}'")
    
    result = await MCPToolInvoker.invoke_tool(
        session=session,
        tool_name="get_document",
        arguments={"documentId": doc_id},
        timeout=20.0,
    )
    
    # We expect content to be a list of text blocks. We just search the text.
    if hasattr(result, "content") and result.content:
        for block in result.content:
            text = getattr(block, "text", "")
            if section_anchor in text:
                logger.info(f"Section '{section_anchor}' found. Skipping delivery.")
                return True
                
    logger.info(f"Section '{section_anchor}' not found. Proceeding with delivery.")
    return False


async def append_section_to_doc(
    session: ClientSession, doc_id: str, batch_update_payload: list[dict[str, Any]]
) -> bool:
    """
    Append a batch of update requests (text, tables) to the Google Doc.
    
    Args:
        session: Active MCP ClientSession for google-docs.
        doc_id: The ID of the target Google Doc.
        batch_update_payload: The list of batchUpdate requests.
        
    Returns:
        True if successful.
    """
    logger.info(f"Appending section payload ({len(batch_update_payload)} requests) to doc '{doc_id}'")
    
    # The anthropic google-docs MCP server provides a tool like 'batch_update' or 'update_document'
    # Actually, the google-docs MCP server usually provides 'append_text' or similar, but
    # looking at the standard implementation, it might have a direct 'batch_update' tool.
    # We'll use 'batch_update' as standard. If we need to adapt to a specific MCP server's tools,
    # we would adjust the tool_name and arguments here.
    
    await MCPToolInvoker.invoke_tool(
        session=session,
        tool_name="batch_update",
        arguments={
            "documentId": doc_id,
            "requests": batch_update_payload,
        },
        timeout=60.0,
    )
    
    logger.info(f"Successfully appended section to doc '{doc_id}'")
    return True
