"""Per-HTTP-request triage uses one webhook row only."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.handoff import SplunkAlertIngest
from services.alert.ingest_background import run_triage_for_ingest


@pytest.mark.asyncio
async def test_run_triage_per_http_request_row_not_all_rest() -> None:
    settings = Settings()
    handoff = SplunkAlertIngest(
        sid="scheduler__admin__search__foo_at_1",
        search_name="New TesT",
        normalized={"host": "desk"},
        results=[{"_time": "2", "User": "bob", "ParentImage": "row2.exe"}],
    )
    enriched = {
        "splunk_results": [
            {"_time": "1", "User": "bob", "ParentImage": "row1.tmp"},
            {"_time": "2", "User": "bob", "ParentImage": "row2.exe"},
        ],
        "splunk_results_row_count": 2,
    }
    trace = {
        "trace_id": "req-2",
        "delivery_hint": "per_row_http_request_same_sid_different_result",
        "request_seq_for_sid": 2,
        "result_fingerprint": "abc",
    }

    with patch(
        "services.alert.ingest_background.run_agent_triage",
        new_callable=AsyncMock,
    ) as single:
        with patch(
            "services.alert.ingest_background.run_agent_triage_all_rows",
            new_callable=AsyncMock,
        ) as batch:
            await run_triage_for_ingest(
                settings,
                handoff,
                enriched,
                ingest_trace=trace,
            )

    single.assert_awaited_once()
    batch.assert_not_awaited()
    body = single.await_args.args[1]
    assert body.sid.endswith("-2")
    assert body.row_index == 1
    assert body.job_row_count == 2
    assert body.splunk_results[0]["ParentImage"] == "row2.exe"
