"""Unit tests for Splunk MCP JSON-RPC client (mocked HTTP)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from config import Settings
from splunk.mcp.client import SplunkMcpClient
from splunk.mcp.errors import McpConnectionError
from tests.http_mocks import mock_httpx_json_response
from tests.mcp_rpc_mock import build_mcp_rpc_mock
from splunk.mcp.tool_registry import McpLogicalTool, resolve_tool_name

_FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    with (_FIXTURES / name).open(encoding="utf-8") as f:
        return json.load(f)


def _mcp_settings() -> Settings:
    return Settings(
        tsoc_mcp_enabled=True,
        splunk_mcp_url="https://splunk.test:8089/services/mcp",
        splunk_mcp_token="test-mcp-token",
        splunk_mcp_verify_ssl=False,
    )


@pytest.mark.asyncio
async def test_resolve_tool_name_aliases():
    tools = ["run_splunk_query", "saia_generate_spl"]
    assert resolve_tool_name(tools, McpLogicalTool.SPLUNK_RUN_QUERY) == "run_splunk_query"
    assert resolve_tool_name(tools, McpLogicalTool.SAIA_GENERATE_SPL) == "saia_generate_spl"


@pytest.mark.asyncio
async def test_mcp_client_initialize_and_list_tools():
    init_body = _load("mcp_initialize.json")
    list_body = _load("mcp_tools_list.json")
    settings = _mcp_settings()
    with patch.object(
        SplunkMcpClient,
        "_rpc",
        build_mcp_rpc_mock(initialize=init_body, tools_list=list_body),
    ):
        client = SplunkMcpClient(settings)
        await client.initialize()
        assert "splunk_get_info" in client.tool_names
        assert resolve_tool_name(client.tool_names, McpLogicalTool.SAIA_GENERATE_SPL)


@pytest.mark.asyncio
async def test_mcp_rpc_retries_transient_splunk_500():
    settings = _mcp_settings()
    init_body = _load("mcp_initialize.json")
    ok_response = mock_httpx_json_response(json_body=init_body)
    fail_response = httpx.Response(
        500,
        text=(
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<response><messages><msg type=\"ERROR\">bad character (49) in reply size</msg></messages></response>"
        ),
        request=httpx.Request("POST", settings.splunk_mcp_url or ""),
    )
    post_mock = AsyncMock(side_effect=[fail_response, ok_response])
    client = SplunkMcpClient(settings)
    with patch.object(client, "_get_http") as get_http:
        http_client = MagicMock()
        http_client.is_closed = False
        http_client.post = post_mock
        get_http.return_value = http_client
        result = await client._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "thinking-soc-hackathon", "version": "0.1.0"},
            },
        )
    assert post_mock.await_count == 2
    assert result.get("serverInfo")


@pytest.mark.asyncio
async def test_mcp_rpc_raises_after_retry_exhausted():
    settings = _mcp_settings()
    fail_response = httpx.Response(
        500,
        text="bad character (49) in reply size",
        request=httpx.Request("POST", settings.splunk_mcp_url or ""),
    )
    post_mock = AsyncMock(return_value=fail_response)
    client = SplunkMcpClient(settings)
    with patch.object(client, "_get_http") as get_http:
        http_client = MagicMock()
        http_client.is_closed = False
        http_client.post = post_mock
        get_http.return_value = http_client
        with pytest.raises(McpConnectionError):
            await client._rpc("initialize", {})
    assert post_mock.await_count == 3


@pytest.mark.asyncio
async def test_mcp_call_tool_saia():
    init_body = _load("mcp_initialize.json")
    list_body = _load("mcp_tools_list.json")
    call_body = _load("mcp_saia_generate_spl.json")
    settings = _mcp_settings()
    with patch.object(
        SplunkMcpClient,
        "_rpc",
        build_mcp_rpc_mock(
            initialize=init_body,
            tools_list=list_body,
            tool_calls=[call_body],
        ),
    ):
        client = SplunkMcpClient(settings)
        raw = await client.call_tool(McpLogicalTool.SAIA_GENERATE_SPL, {"query": "failed logins"})
        assert "search index" in str(raw) or "spl" in str(raw).lower()
