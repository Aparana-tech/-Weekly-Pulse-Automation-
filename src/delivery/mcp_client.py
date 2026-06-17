"""
MCP Client Core.

Manages connections to external Model Context Protocol (MCP) servers and provides
a robust wrapper for tool invocation with timeouts and retries.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Base exception for MCP-related errors."""
    pass


class MCPConnectionError(MCPError):
    """Failed to connect to the MCP server."""
    pass


class MCPToolError(MCPError):
    """Tool invocation failed or returned an error."""
    pass


class MCPTimeoutError(MCPError):
    """Tool invocation timed out."""
    pass


class MCPAuthError(MCPError):
    """Authentication or permission error."""
    pass


class MCPClientManager:
    """Manages connections to MCP servers defined in mcp_servers.json."""

    def __init__(self, config_path: str | Path = "config/mcp_servers.json"):
        self.config_path = Path(config_path)
        self._servers_config: dict[str, dict[str, Any]] = {}
        self._server_failures: dict[str, int] = {}
        self.MAX_FAILURES = 3
        self._load_config()

    def _load_config(self) -> None:
        """Load the MCP server configurations."""
        if not self.config_path.exists():
            logger.warning(f"MCP servers config not found at {self.config_path}")
            return
            
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._servers_config = data.get("mcpServers", {})
        except Exception as e:
            logger.error(f"Failed to load MCP servers config: {e}")
            raise MCPError(f"Failed to load config: {e}") from e

    def get_server_params(self, server_name: str) -> StdioServerParameters:
        """Get the StdioServerParameters for a specific server."""
        if server_name not in self._servers_config:
            raise ValueError(f"Server '{server_name}' not found in configuration.")

        config = self._servers_config[server_name]
        
        # Merge environment variables
        env = os.environ.copy()
        if "env" in config:
            env.update(config["env"])

        return StdioServerParameters(
            command=config["command"],
            args=config.get("args", []),
            env=env,
        )

    @asynccontextmanager
    async def connect(self, server_name: str) -> AsyncGenerator[ClientSession, None]:
        """
        Connect to an MCP server and yield the ClientSession.
        Ensures resources are cleaned up afterward. Implements circuit-breaker pattern.
        """
        if self._server_failures.get(server_name, 0) >= self.MAX_FAILURES:
            raise MCPError(f"Circuit breaker tripped for {server_name}. Too many consecutive failures.")

        params = self.get_server_params(server_name)
        
        try:
            async with stdio_client(params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    self._server_failures[server_name] = 0  # Reset on success
                    yield session
        except Exception as e:
            self._server_failures[server_name] = self._server_failures.get(server_name, 0) + 1
            logger.error(f"Failed to connect to MCP server '{server_name}' (Failure {self._server_failures[server_name]}/{self.MAX_FAILURES}): {e}")
            
            # Identify if it's an auth error based on standard text or error types
            error_str = str(e).lower()
            if "unauthorized" in error_str or "forbidden" in error_str or "auth" in error_str:
                raise MCPAuthError(f"Authentication failed for '{server_name}': {e}") from e
            raise MCPConnectionError(f"Connection failed for '{server_name}': {e}") from e


class MCPToolInvoker:
    """Wrapper to invoke tools on a ClientSession with retries and timeouts."""

    @staticmethod
    async def _invoke_with_timeout(
        session: ClientSession, tool_name: str, arguments: dict[str, Any], timeout: float
    ) -> Any:
        try:
            # We use asyncio.wait_for to enforce the timeout
            result = await asyncio.wait_for(
                session.call_tool(tool_name, arguments=arguments),
                timeout=timeout,
            )
            return result
        except asyncio.TimeoutError as e:
            raise MCPTimeoutError(f"Tool '{tool_name}' timed out after {timeout} seconds.") from e

    @staticmethod
    @retry(
        retry=retry_if_exception_type(MCPTimeoutError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def invoke_tool(
        session: ClientSession,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: float = 30.0,
    ) -> Any:
        """
        Invoke a tool with a timeout and exponential backoff retry.
        Only timeouts are retried automatically.
        """
        try:
            result = await MCPToolInvoker._invoke_with_timeout(session, tool_name, arguments, timeout)
            
            # Check for standard MCP error formatting in the response
            # Assuming MCP call_tool returns a CallToolResult
            if hasattr(result, "isError") and result.isError:
                error_content = result.content
                # Attempt to surface auth errors quickly
                error_str = str(error_content).lower()
                if "unauthorized" in error_str or "forbidden" in error_str or "auth" in error_str or "credentials" in error_str:
                    raise MCPAuthError(f"Authentication error in tool '{tool_name}': {error_content}")
                
                raise MCPToolError(f"Tool '{tool_name}' returned error: {error_content}")
                
            return result
            
        except Exception as e:
            # Re-raise known errors to allow @retry to handle MCPTimeoutError
            if isinstance(e, MCPError):
                raise
            raise MCPToolError(f"Unexpected error calling '{tool_name}': {e}") from e
