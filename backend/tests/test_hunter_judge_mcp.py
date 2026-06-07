"""Hunter/Judge Splunk MCP enrichment (unit tests)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from config import Settings
from models.mcp import McpHunterEvidence, McpJudgeEvidence
from splunk.mcp.hunter_judge_context import (
    _build_hunt_queries,
    build_hunter_mcp_context,
    build_judge_mcp_context,
    format_hunter_mcp_for_prompt,
    mcp_hunter_judge_enabled,
)
from tests.mcp_rpc_mock import build_mcp_rpc_mock


@pytest.fixture
def mcp_settings(test_settings: Settings) -> Settings:
    return test_settings.model_copy(
        update={
            "tsoc_mcp_enabled": True,
            "splunk_mcp_token": "test-token",
            "splunk_mcp_url": "https://splunk.test:8089/services/mcp",
            "tsoc_mcp_hunter_judge_enabled": True,
        }
    )


def test_build_hunt_queries_from_host_and_user() -> None:
    queries = _build_hunt_queries({"host": "web-01", "user": "alice"})
    assert len(queries) == 2
    assert 'host="web-01"' in queries[0]
    assert 'user="alice"' in queries[1]


def test_mcp_hunter_judge_enabled_requires_config(mcp_settings: Settings) -> None:
    assert mcp_hunter_judge_enabled(mcp_settings) is True
    off = mcp_settings.model_copy(update={"tsoc_mcp_enabled": False})
    assert mcp_hunter_judge_enabled(off) is False


@pytest.mark.asyncio
async def test_build_hunter_mcp_context_runs_metadata_and_queries(mcp_settings: Settings) -> None:
    init = {"serverInfo": {"name": "test"}}
    tools = {
        "tools": [
            {"name": "splunk_get_metadata"},
            {"name": "splunk_run_query"},
        ]
    }
    tool_calls = [
        {
            "content": [
                {
                    "type": "text",
                    "text": '[{"sourcetype":"WinEventLog:Security"}]',
                }
            ]
        },
        {
            "structuredContent": {
                "rows": [{"user": "alice", "count": "5"}],
                "total_rows": 1,
            }
        },
        {
            "structuredContent": {
                "rows": [{"host": "web-01", "count": "2"}],
                "total_rows": 1,
            }
        },
    ]
    rpc_mock = build_mcp_rpc_mock(initialize=init, tools_list=tools, tool_calls=tool_calls)

    with patch("splunk.mcp.client.SplunkMcpClient._rpc", rpc_mock):
        ctx = await build_hunter_mcp_context(
            mcp_settings,
            normalized={"host": "web-01", "user": "alice"},
            search_name="Suspicious login",
            splunk_results=[{"host": "web-01"}],
            defender_output={"defender": "benign hypothesis"},
        )

    assert ctx is not None
    assert "splunk_get_metadata:sourcetypes" in ctx.tools_called
    assert ctx.metadata_sourcetypes == ["WinEventLog:Security"]
    assert len(ctx.hunt_queries) == 2
    assert ctx.hunt_queries[0].row_count == 1
    assert "alice" in ctx.hunt_queries[0].summary
    assert format_hunter_mcp_for_prompt(ctx).startswith("\n\n## Splunk MCP hunt evidence")


@pytest.mark.asyncio
async def test_build_judge_mcp_context_saia_and_verify(mcp_settings: Settings) -> None:
    init = {"serverInfo": {"name": "test"}}
    tools = {
        "tools": [
            {"name": "saia_ask_splunk_question"},
            {"name": "splunk_run_query"},
        ]
    }
    tool_calls = [
        {"content": [{"type": "text", "text": "Check auth logs and EDR process trees."}]},
        {"content": [{"type": "text", "text": "Compare failed vs successful logins on the host."}]},
        {
            "structuredContent": {
                "rows": [{"sourcetype": "WinEventLog:Security", "count": "12"}],
                "total_rows": 1,
            }
        },
    ]
    rpc_mock = build_mcp_rpc_mock(initialize=init, tools_list=tools, tool_calls=tool_calls)

    hunter_mcp = McpHunterEvidence(
        tools_called=["splunk_run_query"],
        hunt_queries=[],
    )
    with patch("splunk.mcp.client.SplunkMcpClient._rpc", rpc_mock):
        ctx = await build_judge_mcp_context(
            mcp_settings,
            normalized={"host": "web-01", "user": "alice"},
            search_name="Suspicious login",
            defender_output={"defender": "could be routine"},
            hunter_output={"narrative": "expand auth correlation"},
            hunter_mcp=hunter_mcp,
        )

    assert ctx is not None
    assert isinstance(ctx, McpJudgeEvidence)
    assert len(ctx.saia_answers) == 2
    assert "auth logs" in ctx.saia_answers[0].answer
    assert len(ctx.verification_queries) == 1
    assert ctx.verification_queries[0].row_count == 1


@pytest.mark.asyncio
async def test_build_hunter_mcp_context_returns_none_when_mcp_disabled(
    test_settings: Settings,
) -> None:
    ctx = await build_hunter_mcp_context(
        test_settings,
        normalized={"host": "web-01"},
        search_name="n",
        splunk_results=[],
    )
    assert ctx is None
