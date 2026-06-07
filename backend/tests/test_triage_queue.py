"""Shared Analysis queue builder — parity with /triage/queue."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from services.triage.triage_queue import (
    build_triage_queue_items,
    format_triage_queue_answer,
    is_analysis_queue_question,
)


def test_is_analysis_queue_question() -> None:
    """Legacy helper — SOC chat no longer routes on this; kept for API/docs parity tests."""
    assert is_analysis_queue_question("How many alerts available in SOC? List them")
    assert not is_analysis_queue_question("How many indexed RAG alerts?")


def test_format_empty_queue() -> None:
    ans = format_triage_queue_answer([], track="all")
    assert "empty" in ans.lower()


@pytest.mark.asyncio
async def test_build_triage_queue_skips_invalid_payload(test_settings: Settings) -> None:
    valid_row = {
        "id": 1,
        "tsoc_record_type": "soc_analysis",
        "sid": "real-sid",
        "search_name": "Brute Force",
        "created_at": "2026-05-18T08:24:25+00:00",
        "payload": {
            "tsoc_record_type": "soc_analysis",
            "analysis": {
                    "triage": {
                        "source_track": "security",
                        "triage_score": 90,
                        "confidence_score": 0.9,
                        "priority_rationale": "test",
                        "investigation_priority": "high",
                        "review_verdict": "NEEDS_HUMAN_REVIEW",
                        "needs_human_review": True,
                    }
            },
        },
    }
    junk_row = {
        "id": 99,
        "tsoc_record_type": "soc_analysis",
        "sid": "test-fix",
        "search_name": "t",
        "payload": {"note": "not a real analysis"},
    }

    async def fake_search(_settings, **kwargs):
        if kwargs.get("record_type") == "soc_analysis":
            return [valid_row, junk_row]
        return []

    with patch(
        "services.triage.triage_queue.search_stored_events",
        new_callable=AsyncMock,
        side_effect=fake_search,
    ):
        items = await build_triage_queue_items(test_settings, track="all", limit=50)

    assert len(items) == 1
    assert items[0]["sid"] == "real-sid"
    assert items[0]["triage_score"] == 90


@pytest.mark.asyncio
async def test_build_triage_queue_all_includes_both_tracks_not_global_top_n(
    test_settings: Settings,
) -> None:
    """track=all must not drop a whole track after merging (regression: global [:limit])."""

    def _row(sid: str, rec_type: str, source_track: str, score: int) -> dict:
        return {
            "id": sid,
            "tsoc_record_type": rec_type,
            "sid": sid,
            "search_name": sid,
            "created_at": "2026-05-18T08:24:25+00:00",
            "payload": {
                "tsoc_record_type": rec_type,
                "analysis": {
                    "triage": {
                        "source_track": source_track,
                        "triage_score": score,
                        "confidence_score": 0.9,
                        "priority_rationale": "test",
                        "investigation_priority": "medium",
                        "review_verdict": "NEEDS_HUMAN_REVIEW",
                        "needs_human_review": False,
                    }
                },
            },
        }

    soc_rows = [
        _row(f"sec-{i}", "soc_analysis", "security", 100 - i) for i in range(30)
    ]
    obs_rows = [
        _row(f"obs-{i}", "observability_analysis", "observability", 50 - i)
        for i in range(30)
    ]

    async def fake_search(_settings, **kwargs):
        if kwargs.get("record_type") == "soc_analysis":
            return soc_rows
        if kwargs.get("record_type") == "observability_analysis":
            return obs_rows
        return []

    with patch(
        "services.triage.triage_queue.search_stored_events",
        new_callable=AsyncMock,
        side_effect=fake_search,
    ):
        all_items = await build_triage_queue_items(test_settings, track="all", limit=30)
        sec_items = await build_triage_queue_items(
            test_settings, track="security", limit=30
        )
        obs_items = await build_triage_queue_items(
            test_settings, track="observability", limit=30
        )

    all_sids = {i["sid"] for i in all_items}
    assert len(all_items) == 60
    assert {i["sid"] for i in sec_items}.issubset(all_sids)
    assert {i["sid"] for i in obs_items}.issubset(all_sids)
    assert "obs-0" in all_sids
