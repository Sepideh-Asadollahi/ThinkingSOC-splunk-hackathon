"""Splunk REST enrich uses parent job sid (strips row storage suffix)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import Settings
from models.handoff import SplunkAlertIngest
from services.alert.alert_pipeline import enrich_alert_from_splunk


@pytest.mark.asyncio
async def test_enrich_strips_row_suffix_before_splunk_rest() -> None:
    settings = Settings(splunk_username="admin", splunk_password="secret")
    job_sid = "scheduler__admin__search__New_TesT_at_1780870386.6468"
    handoff = SplunkAlertIngest(
        sid="{0}-2".format(job_sid),
        search_name="New TesT",
        normalized={"host": "we8105desk"},
    )
    client = MagicMock()
    client.login = AsyncMock(return_value="sk")
    client.get_job = AsyncMock(return_value={"entry": [{"content": {"dispatchState": "DONE"}}]})
    client.fetch_all_results = AsyncMock(return_value=[{"host": "we8105desk"}])

    with patch("services.alert.alert_pipeline.SplunkRestClient", return_value=client):
        out = await enrich_alert_from_splunk(handoff, settings)

    client.get_job.assert_awaited_once_with(job_sid, "sk")
    client.fetch_all_results.assert_awaited_once_with(job_sid, "sk")
    assert out["splunk_results_row_count"] == 1
