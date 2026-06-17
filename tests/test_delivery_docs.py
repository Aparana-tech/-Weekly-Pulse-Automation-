"""
Tests for Docs Delivery module.
"""

from __future__ import annotations

import pytest

from src.delivery.docs_delivery import append_section_to_doc, check_section_exists
from src.delivery.mcp_client import MCPToolInvoker


class MockSession:
    pass


@pytest.mark.asyncio
async def test_check_section_exists_found(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MockSession()
    
    async def mock_invoke(*args, **kwargs):
        class MockBlock:
            text = "Test App — Weekly Review Pulse — W23 (2026-06-08 to 2026-06-14)\ntest_app-2026-W23"
        class MockResult:
            content = [MockBlock()]
        return MockResult()
        
    monkeypatch.setattr(MCPToolInvoker, "invoke_tool", mock_invoke)
    
    result = await check_section_exists(session, "doc_123", "test_app-2026-W23") # type: ignore
    assert result is True


@pytest.mark.asyncio
async def test_check_section_exists_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MockSession()
    
    async def mock_invoke(*args, **kwargs):
        class MockBlock:
            text = "Some other text"
        class MockResult:
            content = [MockBlock()]
        return MockResult()
        
    monkeypatch.setattr(MCPToolInvoker, "invoke_tool", mock_invoke)
    
    result = await check_section_exists(session, "doc_123", "test_app-2026-W23") # type: ignore
    assert result is False


@pytest.mark.asyncio
async def test_append_section_to_doc(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MockSession()
    called_args = {}
    
    async def mock_invoke(*args, **kwargs):
        nonlocal called_args
        called_args = kwargs
        return None
        
    monkeypatch.setattr(MCPToolInvoker, "invoke_tool", mock_invoke)
    
    payload = [{"insertText": {"text": "hello"}}]
    result = await append_section_to_doc(session, "doc_123", payload) # type: ignore
    
    assert result is True
    assert called_args["tool_name"] == "batch_update"
    assert called_args["arguments"]["documentId"] == "doc_123"
    assert called_args["arguments"]["requests"] == payload
