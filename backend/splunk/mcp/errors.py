"""Splunk MCP client errors."""


class McpError(Exception):
    """Base MCP error."""


class McpNotConfiguredError(McpError):
    """MCP is disabled or missing URL/token."""


class McpConnectionError(McpError):
    """Could not reach Splunk MCP endpoint."""


class McpToolError(McpError):
    """Tool call failed or returned an error."""

    def __init__(self, message: str, *, tool_name: str | None = None) -> None:
        super().__init__(message)
        self.tool_name = tool_name
