"""Per-row webhook buffer: collect separate POSTs, flush whole job once."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.handoff import SplunkAlertIngest
from services.alert.ingest_accumulator import (
    _reset_for_tests,
    accumulate_ingest_row,
)


def _handoff(result: dict, sid: str = "scheduler__admin__search__buf_at_1") -> SplunkAlertIngest:
    return SplunkAlertIngest(
        sid=sid,
        search_name="Buffered TesT",
        normalized={"host": "desk"},
        results=[result],
    )


@pytest.mark.asyncio
async def test_two_separate_posts_flush_once_with_both_rows() -> None:
    await _reset_for_tests()
    settings = Settings()
    flushed: list[tuple[str, int, list]] = []

    async def _cb(_settings, base_sid, rows, _template):
        flushed.append((base_sid, len(rows), rows))

    row1 = {"_time": "1", "ParentImage": "a.exe"}
    row2 = {"_time": "2", "ParentImage": "b.exe"}
    await accumulate_ingest_row(settings, _handoff(row1), debounce_seconds=0.2, flush_callback=_cb)
    await accumulate_ingest_row(settings, _handoff(row2), debounce_seconds=0.2, flush_callback=_cb)

    await asyncio.sleep(0.4)

    assert len(flushed) == 1
    base_sid, n, rows = flushed[0]
    assert base_sid == "scheduler__admin__search__buf_at_1"
    assert n == 2
    assert {r["ParentImage"] for r in rows} == {"a.exe", "b.exe"}


@pytest.mark.asyncio
async def test_duplicate_post_is_deduped_in_buffer() -> None:
    await _reset_for_tests()
    settings = Settings()
    flushed: list[int] = []

    async def _cb(_settings, _base_sid, rows, _template):
        flushed.append(len(rows))

    same = {"_time": "1", "ParentImage": "a.exe"}
    await accumulate_ingest_row(settings, _handoff(same), debounce_seconds=0.2, flush_callback=_cb)
    await accumulate_ingest_row(settings, _handoff(same), debounce_seconds=0.2, flush_callback=_cb)

    await asyncio.sleep(0.4)
    assert flushed == [1]


@pytest.mark.asyncio
async def test_single_row_flushes_one() -> None:
    await _reset_for_tests()
    settings = Settings()
    flushed: list[int] = []

    async def _cb(_settings, _base_sid, rows, _template):
        flushed.append(len(rows))

    await accumulate_ingest_row(
        settings, _handoff({"_time": "1"}), debounce_seconds=0.2, flush_callback=_cb
    )
    await asyncio.sleep(0.4)
    assert flushed == [1]


@pytest.mark.asyncio
async def test_distinct_sids_flush_independently() -> None:
    await _reset_for_tests()
    settings = Settings()
    flushed: dict[str, int] = {}

    async def _cb(_settings, base_sid, rows, _template):
        flushed[base_sid] = len(rows)

    await accumulate_ingest_row(
        settings, _handoff({"_time": "1"}, sid="job.A"), debounce_seconds=0.2, flush_callback=_cb
    )
    await accumulate_ingest_row(
        settings, _handoff({"_time": "1"}, sid="job.B"), debounce_seconds=0.2, flush_callback=_cb
    )
    await asyncio.sleep(0.4)
    assert flushed == {"job.A": 1, "job.B": 1}


@pytest.mark.asyncio
async def test_buffered_job_runs_all_rows_via_batch() -> None:
    """End to end: buffered rows reach run_agent_triage_all_rows with -1/-2 naming."""
    await _reset_for_tests()
    settings = Settings()
    from services.alert.ingest_background import run_buffered_job_triage

    captured_sids: list[str] = []

    async def _track(_settings, body):
        captured_sids.append(body.sid or "")
        from models.agents import AgentTriageResponse
        from models.agentic_ops import AlertClassificationResult

        return AgentTriageResponse(
            track="security",
            classification=AlertClassificationResult(
                track="security",
                recommended_pipeline="security",
                confidence=0.9,
                classification_source="rules",
                needs_human_routing=False,
                reason="t",
            ),
            agent_summary="ok",
        )

    row1 = {"_time": "1", "ParentImage": "a.exe"}
    row2 = {"_time": "2", "ParentImage": "b.exe"}
    await accumulate_ingest_row(
        settings, _handoff(row1), debounce_seconds=0.2, flush_callback=run_buffered_job_triage
    )
    await accumulate_ingest_row(
        settings, _handoff(row2), debounce_seconds=0.2, flush_callback=run_buffered_job_triage
    )

    with (
        patch("services.alert.ingest_background.persist_splunk_ingest_summary", new_callable=AsyncMock),
        patch("services.alert.ingest_background.schedule_alert_index"),
        patch("services.alert.agent_triage.run_agent_triage", new_callable=AsyncMock, side_effect=_track),
    ):
        await asyncio.sleep(0.5)

    assert captured_sids == [
        "scheduler__admin__search__buf_at_1-1",
        "scheduler__admin__search__buf_at_1-2",
    ]
