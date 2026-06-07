"""Storage sid must stay distinct per Splunk result row."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.agents import AgentTriageRequest
from models.agentic_ops import AlertClassificationResult
from services.alert.agent_triage import run_agent_triage
from services.soc_analysis.analysis_audit import resolve_storage_context


def _classification() -> AlertClassificationResult:
    return AlertClassificationResult(
        track="security",
        recommended_pipeline="security",
        confidence=0.9,
        classification_source="rules",
        needs_human_routing=False,
        reason="test",
    )


def test_resolve_storage_context_preserves_suffixed_sid() -> None:
    sid, idx, job_n = resolve_storage_context(
        sid="1780870386.6468-2",
        splunk_results=[{"ParentImage": "row2.exe"}],
        row_index=0,
        job_row_count=2,
    )
    assert sid == "1780870386.6468-2"
    assert idx == 1
    assert job_n == 2


@pytest.mark.asyncio
async def test_run_agent_triage_keeps_row2_storage_sid(test_settings: Settings) -> None:
    """Single-row slice with ``sid=…-2`` must not collapse to base sid."""
    body = AgentTriageRequest(
        sid="1780870386.6468-2",
        search_name="New TesT",
        normalized={"host": "desk"},
        splunk_results=[{"_time": "2", "ParentImage": "row2.exe"}],
        row_index=1,
        job_row_count=2,
    )

    async def _boom(*_a, **_k):
        raise RuntimeError("stop_after_persist")

    with (
        patch(
            "services.alert.agent_triage.load_inventory_tables",
            new_callable=AsyncMock,
            return_value=([], [], []),
        ),
        patch(
            "services.alert.agent_triage.classify_with_optional_mcp",
            new_callable=AsyncMock,
            return_value=(_classification(), None, False),
        ),
        patch(
            "services.alert.agent_triage.run_analysis",
            new_callable=AsyncMock,
            side_effect=_boom,
        ) as run_analysis,
    ):
        with pytest.raises(RuntimeError, match="stop_after_persist"):
            await run_agent_triage(test_settings, body)

    req = run_analysis.await_args.args[1]
    assert req.sid == "1780870386.6468-2"
    assert req.row_index == 1
    assert run_analysis.await_args.kwargs["analysis_row_index"] == 1
    assert req.splunk_results[0]["ParentImage"] == "row2.exe"
