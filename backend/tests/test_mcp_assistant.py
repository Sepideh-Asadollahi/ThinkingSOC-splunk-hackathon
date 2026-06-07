"""Tests for MCP SPL assistant integration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from config import Settings
from splunk.mcp.client import SplunkMcpClient
from splunk.mcp.spl_assistant import generate_spl_via_mcp
from tests.mcp_rpc_mock import build_mcp_rpc_mock

_FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    with (_FIXTURES / name).open(encoding="utf-8") as f:
        return json.load(f)


def _mcp_settings() -> Settings:
    return Settings(
        tsoc_mcp_enabled=True,
        splunk_mcp_url="https://splunk.test:8089/services/mcp",
        splunk_mcp_token="token",
        splunk_mcp_verify_ssl=False,
        tsoc_mcp_saia_optimize_spl=False,
        tsoc_mcp_saia_explain_spl=False,
    )


@pytest.mark.asyncio
async def test_generate_spl_via_mcp_parses_json_text():
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
        rc, _ = await generate_spl_via_mcp(settings, query="investigate failed login on web-prod-01")
        assert rc is not None
        assert "tstats" in rc.spl.lower() or rc.spl.lower().startswith("search ")
