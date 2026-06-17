"""
Tests for MCP Client wrapper.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from mcp.types import CallToolResult, TextContent

from src.delivery.mcp_client import (
    MCPAuthError,
    MCPClientManager,
    MCPTimeoutError,
    MCPToolError,
    MCPToolInvoker,
)


@pytest.fixture
def mock_config(tmp_path: Any) -> str:
    """Create a temporary config file."""
    config_file = tmp_path / "mcp_servers.json"
    content = """
    {
      "mcpServers": {
        "test-server": {
          "command": "echo",
          "args": ["hello"],
          "env": {"TEST_VAR": "123"}
        }
      }
    }
    """
    config_file.write_text(content)
    return str(config_file)


class TestMCPClientManager:
    def test_load_config_success(self, mock_config: str) -> None:
        manager = MCPClientManager(config_path=mock_config)
        assert "test-server" in manager._servers_config
        assert manager._servers_config["test-server"]["command"] == "echo"

    def test_get_server_params_success(self, mock_config: str) -> None:
        manager = MCPClientManager(config_path=mock_config)
        params = manager.get_server_params("test-server")
        
        assert params.command == "echo"
        assert params.args == ["hello"]
        assert params.env is not None
        assert params.env["TEST_VAR"] == "123"

    def test_get_server_params_missing(self, mock_config: str) -> None:
        manager = MCPClientManager(config_path=mock_config)
        with pytest.raises(ValueError, match="Server 'missing' not found"):
            manager.get_server_params("missing")


class MockClientSession:
    """Mock ClientSession for testing tool invocation."""
    def __init__(self, should_timeout: bool = False, error_content: str | None = None):
        self.should_timeout = should_timeout
        self.error_content = error_content
        self.call_count = 0

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> CallToolResult:
        self.call_count += 1
        
        if self.should_timeout:
            # Sleep longer than the test timeout
            await asyncio.sleep(5.0)
            
        if self.error_content:
            return CallToolResult(
                content=[TextContent(type="text", text=self.error_content)],
                isError=True,
            )
            
        return CallToolResult(
            content=[TextContent(type="text", text="Success")],
            isError=False,
        )


class TestMCPToolInvoker:
    @pytest.mark.asyncio
    async def test_invoke_success(self) -> None:
        session = MockClientSession()
        result = await MCPToolInvoker.invoke_tool(session, "test_tool", {}, timeout=1.0) # type: ignore
        assert result.isError is False
        assert session.call_count == 1

    @pytest.mark.asyncio
    async def test_invoke_timeout_retries(self) -> None:
        session = MockClientSession(should_timeout=True)
        
        # Override the retry wait time for tests so it's fast
        import tenacity
        original_retry = MCPToolInvoker.invoke_tool.retry # type: ignore
        MCPToolInvoker.invoke_tool.retry.wait = tenacity.wait_none() # type: ignore
        
        try:
            with pytest.raises(MCPTimeoutError, match="timed out"):
                # Use a very short timeout
                await MCPToolInvoker.invoke_tool(session, "test_tool", {}, timeout=0.01) # type: ignore
                
            # Stop condition is 3 attempts
            assert session.call_count == 3
        finally:
            MCPToolInvoker.invoke_tool.retry.wait = original_retry.wait # type: ignore

    @pytest.mark.asyncio
    async def test_invoke_auth_error_no_retry(self) -> None:
        session = MockClientSession(error_content="Unauthorized credentials")
        
        with pytest.raises(MCPAuthError, match="Authentication error"):
            await MCPToolInvoker.invoke_tool(session, "test_tool", {}, timeout=1.0) # type: ignore
            
        # Should fail fast, no retries
        assert session.call_count == 1

    @pytest.mark.asyncio
    async def test_invoke_tool_error_no_retry(self) -> None:
        session = MockClientSession(error_content="Missing required parameter: docId")
        
        with pytest.raises(MCPToolError, match="returned error:.*Missing required parameter"):
            await MCPToolInvoker.invoke_tool(session, "test_tool", {}, timeout=1.0) # type: ignore
            
        # Should fail fast, no retries
        assert session.call_count == 1
