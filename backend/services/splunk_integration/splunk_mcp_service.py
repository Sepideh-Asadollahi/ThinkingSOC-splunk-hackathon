"""Orchestration helpers for Splunk MCP (status, health)."""

from __future__ import annotations

import logging
from typing import Optional

from config import Settings, mcp_configured, splunk_mcp_url_for
from models.mcp import McpStatusResponse
from splunk.mcp.client import SplunkMcpClient
from splunk.mcp.errors import McpConnectionError, McpNotConfiguredError, McpToolError
from splunk.mcp.tool_registry import McpLogicalTool, resolve_tool_name, saia_tool_names

logger = logging.getLogger(__name__)


async def is_saia_available(settings: Settings) -> bool:
    """True when MCP is configured, reachable, and ``saia_generate_spl`` is listed."""
    status = await get_mcp_status(settings)
    return bool(status.configured and status.connected and status.saia_available)


async def get_mcp_status(settings: Settings) -> McpStatusResponse:
    """Probe MCP configuration and connectivity for judges."""
    if not mcp_configured(settings):
        return McpStatusResponse(
            configured=False,
            connected=False,
            message="Set TSOC_MCP_ENABLED=true, SPLUNK_MCP_TOKEN, and SPLUNK_MCP_URL (or SPLUNK_MGMT_URL).",
        )

    url = splunk_mcp_url_for(settings)
    try:
        client = SplunkMcpClient(settings)
        ok = await client.ping()
        tools = client.tool_names
        saia = bool(resolve_tool_name(tools, McpLogicalTool.SAIA_GENERATE_SPL)) or bool(saia_tool_names(tools))
        return McpStatusResponse(
            configured=True,
            connected=ok,
            url=url,
            server_info=client.server_info,
            tools=tools,
            saia_available=saia,
            message=None if ok else "MCP initialize failed; check token, app 7931, and URL.",
        )
    except McpNotConfiguredError as e:
        return McpStatusResponse(configured=False, connected=False, message=str(e))
    except (McpConnectionError, McpToolError) as e:
        logger.warning("mcp status error: %s", e)
        return McpStatusResponse(
            configured=True,
            connected=False,
            url=url,
            message=str(e),
        )
