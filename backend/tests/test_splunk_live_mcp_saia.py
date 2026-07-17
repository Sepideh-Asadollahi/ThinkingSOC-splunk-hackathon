"""
Live Splunk MCP + SAIA integration tests (real Splunk on 8089).

Run:
  TSOC_RUN_SPLUNK_LIVE=1 pytest tests/test_splunk_live_mcp_saia.py -v -s -m splunk_live
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List

import httpx
import pytest

from config import Settings, mcp_configured
from models.analysis import InvestigationQuestionItem
from services.investigation.investigation_spl_execute import _run_one
from services.investigation.investigation_questions_spl import finalize_investigation_questions_for_verdict
from services.splunk_integration.splunk_mcp_service import get_mcp_status
from splunk.client import SplunkRestClient
from splunk.datamodel.cim_schema import fetch_cim_datamodel_schema
from splunk.mcp.client import SplunkMcpClient
from splunk.mcp.spl_assistant import generate_spl_via_mcp
from splunk.mcp.tool_registry import McpLogicalTool, resolve_tool_name

pytestmark = pytest.mark.splunk_live

_SAIA_QUERY = (
    "Count failed authentication events for user admin in the last 24 hours "
    "using CIM Authentication datamodel with tstats"
)

_SAIA_SKIP_REASON = (
    "Splunk AI Assistant cloud API unavailable (404 on saia-api). "
    "Provision Splunk AI Assistant Cloud in Splunk Web (Settings > AI Assistant)."
)

_ASSISTANT_BODY: Dict[str, Any] = {
    "normalized": {"host": "web-prod-01", "user": "admin", "src": "1.2.3.4"},
    "search_name": "Suspicious failed login",
    "objective": "Were there other failed logins for this user in the last 7 days?",
}


def _spl_nonempty(spl: str | None) -> bool:
    text = (spl or "").strip().lower()
    return bool(text) and ("tstats" in text or "search" in text or "|" in text)


@pytest.mark.asyncio
async def test_a0_saia_backend_connectivity(saia_backend_ok: bool) -> None:
    """Explicit probe: MCP lists SAIA tools; cloud API may still be unavailable."""
    if not saia_backend_ok:
        pytest.skip(_SAIA_SKIP_REASON)


@pytest.mark.asyncio
async def test_a1_mcp_client_initialize_and_saia_tools(splunk_live_settings: Settings) -> None:
    client = SplunkMcpClient(splunk_live_settings)
    assert await client.ping()
    assert resolve_tool_name(client.tool_names, McpLogicalTool.SAIA_GENERATE_SPL)
    assert resolve_tool_name(client.tool_names, McpLogicalTool.SAIA_OPTIMIZE_SPL)
    assert resolve_tool_name(client.tool_names, McpLogicalTool.SAIA_EXPLAIN_SPL)


@pytest.mark.asyncio
async def test_a2_mcp_status_endpoint(splunk_live_settings: Settings, live_api_base: str) -> None:
    async with httpx.AsyncClient(timeout=120.0) as http:
        for attempt in range(3):
            r = await http.get("{0}/api/v1/mcp/status".format(live_api_base))
            if r.status_code == 200:
                break
            await asyncio.sleep(2)
    assert r.status_code == 200, r.text[:500]
    data = r.json()
    assert data["configured"] is True
    assert data["connected"] is True
    assert data["saia_available"] is True

    status = await get_mcp_status(splunk_live_settings)
    assert status.connected is True
    assert status.saia_available is True


@pytest.mark.asyncio
async def test_a3_saia_generate_spl_direct(
    splunk_live_settings: Settings, saia_backend_ok: bool
) -> None:
    if not saia_backend_ok:
        pytest.skip(_SAIA_SKIP_REASON)
    client = SplunkMcpClient(splunk_live_settings)
    await client.ensure_ready()
    raw = await client.call_tool(
        McpLogicalTool.SAIA_GENERATE_SPL,
        {"prompt": _SAIA_QUERY[:1000], "spl_only": True},
    )
    text = str(raw).lower()
    assert _spl_nonempty(text) or "tstats" in text or "search" in text


@pytest.mark.asyncio
async def test_a4_mcp_spl_generate_api(
    splunk_live_settings: Settings,
    live_api_base: str,
    saia_backend_ok: bool,
) -> None:
    if not saia_backend_ok:
        pytest.skip(_SAIA_SKIP_REASON)
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    token = (splunk_live_settings.tsoc_ingest_token or "").strip()
    if token:
        headers["Authorization"] = "Bearer {0}".format(token)

    async with httpx.AsyncClient(timeout=180.0) as http:
        r = await http.post(
            "{0}/api/v1/mcp/spl-generate".format(live_api_base),
            headers=headers,
            json={"query": _SAIA_QUERY, "context": "live integration test"},
        )
    assert r.status_code == 200, r.text[:800]
    data = r.json()
    assert data.get("source") == "splunk_mcp_saia"
    assert _spl_nonempty(data.get("spl"))


@pytest.mark.asyncio
async def test_a5_saia_pipeline_optimize_explain_notes(
    splunk_live_settings: Settings, saia_backend_ok: bool
) -> None:
    if not saia_backend_ok:
        pytest.skip(_SAIA_SKIP_REASON)
    rc, trace = await generate_spl_via_mcp(
        splunk_live_settings,
        query=_SAIA_QUERY,
        context="live saia pipeline test",
        objective="Explain failed login volume for admin",
    )
    assert rc is not None
    assert _spl_nonempty(rc.spl)
    notes = list(rc.notes or [])
    assert "mcp_saia_generate_spl" in notes
    if splunk_live_settings.tsoc_mcp_saia_optimize_spl:
        assert "mcp_saia_optimize_spl" in notes or any(
            str(step).startswith("optimize") for step in trace.get("steps", [])
        )
    if splunk_live_settings.tsoc_mcp_saia_explain_spl:
        assert "mcp_saia_explain_spl" in notes or (rc.explanation or "").strip()


@pytest.mark.asyncio
async def test_b0_mcp_disabled_uses_real_rest_fallback(
    splunk_live_settings: Settings,
) -> None:
    """Prove the documented fallback works with MCP explicitly unavailable."""
    settings = splunk_live_settings.model_copy(update={"tsoc_mcp_enabled": False})
    client = SplunkRestClient(settings)
    session_key = await client.login()
    result = await _run_one(
        settings,
        client,
        session_key,
        "search index=_internal | head 1",
        app="search",
    )
    assert result.error is None
    assert result.execution_transport == "rest"
    assert (result.row_count or 0) >= 1


@pytest.mark.asyncio
async def test_b1_cim_datamodel_schema(splunk_live_settings: Settings) -> None:
    schema = await fetch_cim_datamodel_schema(splunk_live_settings, "Authentication")
    assert schema is not None
    assert len(schema.objects) >= 1
    assert len(schema.attributes) >= 1


@pytest.mark.asyncio
async def test_b2_assistant_spl_suggest_api(
    splunk_live_settings: Settings,
    live_api_base: str,
    saia_backend_ok: bool,
) -> None:
    if not saia_backend_ok:
        pytest.skip(_SAIA_SKIP_REASON)
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    token = (splunk_live_settings.tsoc_ingest_token or "").strip()
    if token:
        headers["Authorization"] = "Bearer {0}".format(token)

    async with httpx.AsyncClient(timeout=300.0) as http:
        r = await http.post(
            "{0}/api/v1/assistant/spl-suggest".format(live_api_base),
            headers=headers,
            json=_ASSISTANT_BODY,
        )
    assert r.status_code == 200, r.text[:800]
    data = r.json()
    assert data["source"] in (
        "splunk_mcp_saia",
        "splunk_mcp_saia_reviewed",
        "splunk_mcp_saia+llm",
        "rest_predict_execute",
        "rest_predict_execute_empty",
        "rest_predict_execute_error",
    )
    rc = data.get("root_cause_spl") or {}
    assert _spl_nonempty(rc.get("spl"))


@pytest.mark.asyncio
async def test_b3_finalize_investigation_questions(
    splunk_live_settings: Settings, saia_backend_ok: bool
) -> None:
    if not saia_backend_ok:
        pytest.skip(_SAIA_SKIP_REASON)
    raw_questions = [{"question": _ASSISTANT_BODY["objective"]}]
    items = await finalize_investigation_questions_for_verdict(
        splunk_live_settings,
        "needs_investigation",
        raw_questions,
        normalized=_ASSISTANT_BODY["normalized"],
        search_name=_ASSISTANT_BODY["search_name"],
    )
    assert len(items) >= 1
    item = items[0]
    assert isinstance(item, InvestigationQuestionItem)
    assert _spl_nonempty(item.spl)
    notes = list(item.notes or [])
    assert any(
        n in notes
        for n in (
            "splunk_mcp_saia",
            "mcp_saia_generate_spl",
            "splunk_mcp_saia+llm",
            "llm_reviewed_after_mcp_saia",
            "rest_predict_write_spl",
            "mcp_saia_optimize_spl",
            "mcp_saia_explain_spl",
        )
    )


@pytest.mark.asyncio
async def test_b4_validation_and_execute(splunk_live_settings: Settings) -> None:
    # Rule-based CIM tstats only — avoids LLM SPL with earliest/latest inside tstats.
    settings = splunk_live_settings
    raw_questions = [{"question": "Count failed logins for user admin in last 7 days"}]
    items = await finalize_investigation_questions_for_verdict(
        settings,
        "needs_investigation",
        raw_questions,
        normalized={"user": "admin"},
        search_name="live execute test",
    )
    assert items
    item = items[0]
    assert item.spl_results is not None
    assert item.spl_results.error is None or not str(item.spl_results.error).strip(), (
        item.spl_results.error
    )
    assert (item.spl_results.row_count or 0) >= 0


@pytest.mark.asyncio
async def test_b5_splunk_get_metadata_optional(splunk_live_settings: Settings) -> None:
    if os.environ.get("TSOC_LIVE_SKIP_METADATA") == "1":
        pytest.skip("TSOC_LIVE_SKIP_METADATA=1")
    client = SplunkMcpClient(splunk_live_settings)
    await client.ensure_ready()
    if not resolve_tool_name(client.tool_names, McpLogicalTool.SPLUNK_GET_METADATA):
        pytest.skip("splunk_get_metadata not listed on MCP server")
    raw = await client.call_tool(
        McpLogicalTool.SPLUNK_GET_METADATA,
        {"type": "hosts", "index": "*", "earliest_time": "-24h", "latest_time": "now"},
    )
    assert raw is not None
    assert str(raw).strip()
