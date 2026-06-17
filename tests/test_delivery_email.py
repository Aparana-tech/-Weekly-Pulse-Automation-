"""
Tests for Email Delivery module.
"""

from __future__ import annotations

import pytest

from src.delivery.email_delivery import deliver_email
from src.delivery.mcp_client import MCPToolInvoker


class MockSession:
    pass


@pytest.mark.asyncio
async def test_deliver_email_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MockSession()
    called_args = {}
    
    async def mock_invoke(*args, **kwargs):
        nonlocal called_args
        called_args = kwargs
        class MockBlock:
            text = "draft_123"
        class MockResult:
            content = [MockBlock()]
        return MockResult()
        
    monkeypatch.setattr(MCPToolInvoker, "invoke_tool", mock_invoke)
    
    content = {"subject": "Test Subject", "html_body": "<html></html>"}
    recipients = ["test@example.com", "test2@example.com"]
    
    result = await deliver_email(session, content, recipients, "draft") # type: ignore
    
    assert result == "draft_123"
    assert called_args["tool_name"] == "create_draft"
    assert called_args["arguments"]["to"] == "test@example.com, test2@example.com"
    assert called_args["arguments"]["subject"] == "Test Subject"
    assert called_args["arguments"]["body"] == "<html></html>"


@pytest.mark.asyncio
async def test_deliver_email_send(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MockSession()
    called_args = {}
    
    async def mock_invoke(*args, **kwargs):
        nonlocal called_args
        called_args = kwargs
        class MockBlock:
            text = "msg_123"
        class MockResult:
            content = [MockBlock()]
        return MockResult()
        
    monkeypatch.setattr(MCPToolInvoker, "invoke_tool", mock_invoke)
    
    content = {"subject": "Test Subject", "html_body": "<html></html>"}
    recipients = ["test@example.com"]
    
    result = await deliver_email(session, content, recipients, "send") # type: ignore
    
    assert result == "msg_123"
    assert called_args["tool_name"] == "send_email"
    assert called_args["arguments"]["to"] == "test@example.com"
