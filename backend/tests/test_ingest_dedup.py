"""Concurrent duplicate triage guard for per-row webhook delivery."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.handoff import SplunkAlertIngest
from services.alert.ingest_background import run_triage_for_ingest
from services.alert.ingest_dedup import (
    _reset_for_tests,
    claim_storage_sid,
    release_storage_sid,
)


@pytest.mark.asyncio
async def test_claim_same_sid_twice_blocks_second() -> None:
    await _reset_for_tests()
    assert await claim_storage_sid("job.dedup.a-1") is True
    assert await claim_storage_sid("job.dedup.a-1") is False


@pytest.mark.asyncio
async def test_distinct_sids_both_claimable() -> None:
    await _reset_for_tests()
    assert await claim_storage_sid("job.dedup.b-1") is True
    assert await claim_storage_sid("job.dedup.b-2") is True


@pytest.mark.asyncio
async def test_release_allows_reclaim() -> None:
    await _reset_for_tests()
    assert await claim_storage_sid("job.dedup.c-1") is True
    await release_storage_sid("job.dedup.c-1")
    assert await claim_storage_sid("job.dedup.c-1") is True


def _handoff(result: dict) -> SplunkAlertIngest:
    return SplunkAlertIngest(
        sid="scheduler__admin__search__dedup_at_1",
        search_name="Dedup TesT",
        normalized={"host": "desk"},
        results=[result],
    )


@pytest.mark.asyncio
async def test_run_triage_skips_duplicate_concurrent_same_row() -> None:
    """Two POSTs that map to the same storage sid → triage runs once."""
    await _reset_for_tests()
    settings = Settings()
    same_row = {"_time": "1", "User": "bob", "ParentImage": "row1.exe"}
    enriched = {"splunk_results": [same_row], "splunk_results_row_count": 1}

    with patch(
        "services.alert.ingest_background.run_agent_triage",
        new_callable=AsyncMock,
    ) as single:
        await run_triage_for_ingest(settings, _handoff(same_row), enriched)
        await run_triage_for_ingest(settings, _handoff(same_row), enriched)

    single.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_triage_allows_distinct_rows() -> None:
    """Two POSTs mapping to different rows → both analyzed."""
    await _reset_for_tests()
    settings = Settings()
    row1 = {"_time": "1", "User": "bob", "ParentImage": "row1.exe"}
    row2 = {"_time": "2", "User": "bob", "ParentImage": "row2.exe"}
    enriched = {"splunk_results": [row1, row2], "splunk_results_row_count": 2}

    with patch(
        "services.alert.ingest_background.run_agent_triage",
        new_callable=AsyncMock,
    ) as single:
        await run_triage_for_ingest(settings, _handoff(row1), enriched)
        await run_triage_for_ingest(settings, _handoff(row2), enriched)

    assert single.await_count == 2
    sids = sorted(call.args[1].sid for call in single.await_args_list)
    assert sids == ["scheduler__admin__search__dedup_at_1-1", "scheduler__admin__search__dedup_at_1-2"]


@pytest.mark.asyncio
async def test_two_posts_with_unmatchable_results_get_distinct_rows() -> None:
    """Regression: webhook results that don't fingerprint-match REST must not collapse to -1/-1.

    Both POSTs carry a webhook ``result`` whose serialization differs from REST rows,
    so fingerprint matching fails. Using HTTP request order, POST 1 → row 0 (-1),
    POST 2 → row 1 (-2). No duplicates.
    """
    await _reset_for_tests()
    settings = Settings()
    rest_rows = [
        {"_time": "2018-08-24 21:18:41", "User": "bob", "ParentImage": "r1.exe"},
        {"_time": "2018-08-24 21:18:50", "User": "bob", "ParentImage": "r2.exe"},
    ]
    enriched = {"splunk_results": rest_rows, "splunk_results_row_count": 2}
    # Webhook serialization differs (epoch _time, extra key) → no fingerprint/field match.
    webhook_a = {"_time": "1535145521", "raw": "evt-a"}
    webhook_b = {"_time": "1535145530", "raw": "evt-b"}
    trace_a = {"trace_id": "a", "request_seq_for_sid": 1, "delivery_hint": "x"}
    trace_b = {"trace_id": "b", "request_seq_for_sid": 2, "delivery_hint": "x"}

    with patch(
        "services.alert.ingest_background.run_agent_triage",
        new_callable=AsyncMock,
    ) as single:
        await run_triage_for_ingest(settings, _handoff(webhook_a), enriched, ingest_trace=trace_a)
        await run_triage_for_ingest(settings, _handoff(webhook_b), enriched, ingest_trace=trace_b)

    assert single.await_count == 2
    sids = sorted(call.args[1].sid for call in single.await_args_list)
    assert sids == ["scheduler__admin__search__dedup_at_1-1", "scheduler__admin__search__dedup_at_1-2"]
    # Each analyzed a distinct REST row.
    analyzed_rows = sorted(call.args[1].splunk_results[0]["ParentImage"] for call in single.await_args_list)
    assert analyzed_rows == ["r1.exe", "r2.exe"]


@pytest.mark.asyncio
async def test_run_triage_failure_releases_claim_for_retry() -> None:
    await _reset_for_tests()
    settings = Settings()
    row = {"_time": "1", "User": "bob", "ParentImage": "row1.exe"}
    enriched = {"splunk_results": [row], "splunk_results_row_count": 1}

    with patch(
        "services.alert.ingest_background.run_agent_triage",
        new_callable=AsyncMock,
        side_effect=[RuntimeError("boom"), None],
    ) as single:
        with pytest.raises(RuntimeError, match="boom"):
            await run_triage_for_ingest(settings, _handoff(row), enriched)
        # claim released on failure → retry proceeds
        await run_triage_for_ingest(settings, _handoff(row), enriched)

    assert single.await_count == 2
