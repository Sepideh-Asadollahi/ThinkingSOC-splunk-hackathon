"""Tests for saia_optimize_spl and saia_explain_spl post-processing."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from splunk.mcp.client import SplunkMcpClient
from splunk.mcp.spl_assistant import generate_spl_via_mcp
from tests.mcp_rpc_mock import build_mcp_rpc_mock

_FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    with (_FIXTURES / name).open(encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_saia_pipeline_generate_optimize_explain():
    init_body = _load("mcp_initialize.json")
    list_body = _load("mcp_tools_list.json")
    gen_body = _load("mcp_saia_generate_spl.json")
    opt_body = _load("mcp_saia_optimize_spl.json")
    explain_body = _load("mcp_saia_explain_spl.json")
    settings = Settings(
        tsoc_mcp_enabled=True,
        splunk_mcp_url="https://splunk.test:8089/services/mcp",
        splunk_mcp_token="token",
        tsoc_saia_llm_prepare_prompt=False,
        tsoc_mcp_saia_optimize_spl=True,
        tsoc_mcp_saia_explain_spl=True,
    )

    with patch.object(
        SplunkMcpClient,
        "_rpc",
        build_mcp_rpc_mock(
            initialize=init_body,
            tools_list=list_body,
            tool_calls=[gen_body, opt_body, explain_body],
        ),
    ):
        from models.analysis import RootCauseSplValidation

        async def _mock_validate(_settings, rc, **kwargs):
            return RootCauseSplValidation(method="skipped", valid=True)

        with patch(
            "splunk.mcp.saia.pipeline.validate_root_cause_spl",
            new_callable=AsyncMock,
            side_effect=_mock_validate,
        ):
            rc, trace = await generate_spl_via_mcp(
                settings,
                query="investigate failed login",
                context="failed login alert",
            )

    assert rc is not None
    assert "sort" in rc.spl
    assert "analyst" in rc.explanation.lower() or "login" in rc.explanation.lower()
    assert "mcp_saia_optimize_spl" in rc.notes
    assert "mcp_saia_explain_spl" in rc.notes
    assert "optimize" in trace.get("steps", [])
