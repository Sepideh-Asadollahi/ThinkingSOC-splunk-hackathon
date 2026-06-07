"""Per-row agent triage."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.agents import AgentTriageRequest, AgentTriageResponse
from models.agentic_ops import AlertClassificationResult
from services.alert.agent_triage import run_agent_triage_all_rows


def _classification() -> AlertClassificationResult:
    return AlertClassificationResult(
        track="security",
        recommended_pipeline="security",
        confidence=0.9,
        classification_source="rules",
        needs_human_routing=False,
        reason="test",
    )


def _triage_response() -> AgentTriageResponse:
    return AgentTriageResponse(
        track="security",
        classification=_classification(),
        agent_summary="ok",
    )


@pytest.mark.asyncio
async def test_run_agent_triage_all_rows_sequential_order(test_settings: Settings) -> None:
    """Row 2 starts only after row 1 completes (await order)."""
    order: list[str] = []

    async def _track_triage(_settings: Settings, body: AgentTriageRequest) -> AgentTriageResponse:
        order.append(body.sid or "")
        return _triage_response()

    body = AgentTriageRequest(
        sid="1780870386.6468",
        search_name="New TesT",
        splunk_results=[{"a": 1}, {"a": 2}],
    )
    with patch(
        "services.alert.agent_triage.run_agent_triage",
        new_callable=AsyncMock,
        side_effect=_track_triage,
    ):
        await run_agent_triage_all_rows(test_settings, body)

    assert order == ["1780870386.6468-1", "1780870386.6468-2"]


@pytest.mark.asyncio
async def test_run_agent_triage_all_rows_continues_after_row_error(test_settings: Settings) -> None:
    body = AgentTriageRequest(
        sid="1780870386.6468",
        search_name="New TesT",
        splunk_results=[{"a": 1}, {"a": 2}],
    )
    with patch(
        "services.alert.agent_triage.run_agent_triage",
        new_callable=AsyncMock,
        side_effect=[RuntimeError("row1"), _triage_response()],
    ) as triage:
        out = await run_agent_triage_all_rows(test_settings, body)

    assert triage.await_count == 2
    assert len(out) == 1


@pytest.mark.asyncio
async def test_run_agent_triage_all_rows_two_rows(test_settings: Settings) -> None:
    body = AgentTriageRequest(
        sid="1780870386.6468",
        search_name="New TesT",
        normalized={"host": "we8105desk"},
        splunk_results=[
            {"Computer": "we8105desk", "User": "bob", "_time": "2018-08-24 21:18:41"},
            {"Computer": "we8105desk", "User": "bob", "_time": "2018-08-24 21:18:50"},
        ],
    )
    with patch(
        "services.alert.agent_triage.run_agent_triage",
        new_callable=AsyncMock,
        side_effect=[_triage_response(), _triage_response()],
    ) as triage:
        out = await run_agent_triage_all_rows(test_settings, body)

    assert len(out) == 2
    assert triage.await_count == 2
    first_body = triage.await_args_list[0].args[1]
    second_body = triage.await_args_list[1].args[1]
    assert first_body.sid == "1780870386.6468-1"
    assert second_body.sid == "1780870386.6468-2"
    assert first_body.splunk_results[0]["_time"] == "2018-08-24 21:18:41"
    assert second_body.splunk_results[0]["_time"] == "2018-08-24 21:18:50"


@pytest.mark.asyncio
async def test_run_agent_triage_all_rows_single_row_no_suffix(test_settings: Settings) -> None:
    body = AgentTriageRequest(
        sid="1780870386.6468",
        search_name="solo",
        splunk_results=[{"host": "h1"}],
    )
    with patch(
        "services.alert.agent_triage.run_agent_triage",
        new_callable=AsyncMock,
        return_value=_triage_response(),
    ) as triage:
        out = await run_agent_triage_all_rows(test_settings, body)

    assert len(out) == 1
    assert triage.await_args.args[1].sid == "1780870386.6468"


@pytest.mark.asyncio
async def test_run_agent_triage_all_rows_respects_max_rows(test_settings: Settings) -> None:
    body = AgentTriageRequest(
        sid="job.1",
        search_name="cap",
        splunk_results=[{"i": 0}, {"i": 1}, {"i": 2}],
    )
    with patch(
        "services.alert.agent_triage.run_agent_triage",
        new_callable=AsyncMock,
        return_value=_triage_response(),
    ) as triage:
        out = await run_agent_triage_all_rows(test_settings, body, max_rows=2)

    assert len(out) == 2
    assert triage.await_count == 2
    assert triage.await_args_list[0].args[1].sid == "job.1-1"
    assert triage.await_args_list[1].args[1].sid == "job.1-2"


@pytest.mark.asyncio
async def test_run_agent_triage_all_rows_stop_on_first_error(test_settings: Settings) -> None:
    body = AgentTriageRequest(
        sid="job.1",
        search_name="stop",
        splunk_results=[{"i": 0}, {"i": 1}],
    )
    with patch(
        "services.alert.agent_triage.run_agent_triage",
        new_callable=AsyncMock,
        side_effect=RuntimeError("fail"),
    ) as triage:
        with pytest.raises(RuntimeError, match="fail"):
            await run_agent_triage_all_rows(test_settings, body, stop_on_first_error=True)

    assert triage.await_count == 1
