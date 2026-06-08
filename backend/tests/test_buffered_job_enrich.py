"""Buffered webhook flush must load full Splunk job rows via REST when possible."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.handoff import SplunkAlertIngest
from services.alert.ingest_background import run_buffered_job_triage


@pytest.mark.asyncio
async def test_buffered_flush_enriches_from_rest_before_triage() -> None:
    settings = Settings()
    webhook_row = {"ParentImage": "row1.exe", "User": "bob"}
    rest_rows = [
        {"ParentImage": "row1.exe", "User": "bob"},
        {"ParentImage": "row2.exe", "User": "bob"},
    ]
    template = SplunkAlertIngest(
        sid="scheduler__admin__search__job_at_1",
        search_name="New TesT",
        normalized=webhook_row,
        results=[webhook_row],
    )
    enriched = {
        "splunk_results": rest_rows,
        "splunk_results_row_count": 2,
        "enrichment_source": "splunk_rest",
    }

    with (
        patch(
            "services.alert.ingest_background.enrich_alert_from_splunk",
            new_callable=AsyncMock,
            return_value=enriched,
        ) as enrich,
        patch(
            "services.alert.ingest_background.run_post_ingest",
            new_callable=AsyncMock,
        ) as post_ingest,
    ):
        await run_buffered_job_triage(
            settings,
            "scheduler__admin__search__job_at_1",
            [webhook_row],
            template,
        )

    enrich.assert_awaited_once()
    post_ingest.assert_awaited_once()
    handoff = post_ingest.await_args.args[1]
    enriched_arg = post_ingest.await_args.args[2]
    assert len(handoff.results) == 2
    assert enriched_arg["splunk_results_row_count"] == 2
