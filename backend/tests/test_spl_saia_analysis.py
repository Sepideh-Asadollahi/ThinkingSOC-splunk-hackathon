"""SAIA MCP explain/optimize on investigation SPL during SOC analysis."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.analysis import InvestigationQuestionItem, SplSaiaAnalysis
from services.investigation.investigation_questions_spl import fill_investigation_spl
from services.investigation.spl_saia_analysis import analyze_investigation_spl_with_saia
from splunk.mcp.client import SplunkMcpClient
from tests.mcp_rpc_mock import build_mcp_rpc_mock

_FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    with (_FIXTURES / name).open(encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_analyze_investigation_spl_with_saia_optimize_explain():
    init_body = _load("mcp_initialize.json")
    list_body = _load("mcp_tools_list.json")
    opt_body = _load("mcp_saia_optimize_spl.json")
    explain_body = _load("mcp_saia_explain_spl.json")
    settings = Settings(
        tsoc_mcp_enabled=True,
        splunk_mcp_url="https://splunk.test:8089/services/mcp",
        splunk_mcp_token="token",
        tsoc_analysis_saia_spl_review=True,
        tsoc_mcp_saia_optimize_spl=True,
        tsoc_mcp_saia_explain_spl=True,
    )
    draft = '| datamodel Authentication | search user="admin" | stats count'

    with patch.object(
        SplunkMcpClient,
        "_rpc",
        build_mcp_rpc_mock(
            initialize=init_body,
            tools_list=list_body,
            tool_calls=[opt_body, explain_body],
        ),
    ):
        final_spl, final_expl, analysis = await analyze_investigation_spl_with_saia(
            settings,
            spl=draft,
            explanation="draft",
            question="Who failed login?",
            search_name="auth alert",
        )

    assert analysis is not None
    assert "optimize" in analysis.steps
    assert "explain" in analysis.steps
    assert final_expl
    assert "login" in final_expl.lower() or "analyst" in final_expl.lower()
    assert final_spl


@pytest.mark.asyncio
async def test_fill_investigation_attaches_saia_analysis(test_settings: Settings):
    settings = test_settings.model_copy(
        update={
            "tsoc_analysis_saia_spl_review": True,
            "tsoc_mcp_enabled": True,
            "splunk_mcp_url": "https://splunk.test:8089/services/mcp",
            "splunk_mcp_token": "token",
            "tsoc_mcp_saia_optimize_spl": False,
            "tsoc_mcp_saia_explain_spl": True,
        }
    )
    items = [InvestigationQuestionItem(question="Failed logins?", spl="")]
    saia = SplSaiaAnalysis(
        explanation="SAIA explains the search.",
        optimized=False,
        steps=["explain"],
    )

    with patch(
        "services.investigation.investigation_questions_spl.enrich_investigation_item_with_saia",
        new_callable=AsyncMock,
    ) as mock_saia:
        async def _attach(_s, item, **kw):
            return item.model_copy(
                update={
                    "spl": "search index=main | stats count",
                    "spl_saia_analysis": saia,
                    "notes": ["mcp_saia_analysis"],
                }
            )

        mock_saia.side_effect = _attach
        out, source = await fill_investigation_spl(
            settings,
            items,
            {"user": "admin"},
            search_name="auth alert",
        )

    assert mock_saia.await_count == 1
    assert "+saia" in source
    assert out[0].spl_saia_analysis is not None
    assert out[0].spl_saia_analysis.explanation == "SAIA explains the search."
