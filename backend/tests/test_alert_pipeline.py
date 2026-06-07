from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import Settings
from models.handoff import SplunkAlertIngest
from services.alert.alert_pipeline import _looks_like_splunk_job_sid, enrich_alert_from_splunk


def test_looks_like_splunk_job_sid():
    assert _looks_like_splunk_job_sid("scheduler__admin__search__RUID_123") is True
    assert _looks_like_splunk_job_sid("proofpoint_phish_click_t8372") is False


@pytest.mark.asyncio
async def test_enrich_uses_normalized_for_demo_sid(test_settings: Settings):
    handoff = SplunkAlertIngest(
        sid="proofpoint_phish_click_t8372",
        normalized={"user": "WAYNECORPINC\\bwayne", "host": "DESKTOP-BRUCE"},
    )
    out = await enrich_alert_from_splunk(handoff, test_settings)
    assert out["splunk_results_row_count"] == 1
    assert out["splunk_results"][0]["host"] == "DESKTOP-BRUCE"
    assert out["enrichment_source"] == "normalized_demo_sid"


@pytest.mark.asyncio
async def test_enrich_uses_inline_results(test_settings: Settings):
    handoff = SplunkAlertIngest(
        sid="proofpoint_phish_click_t8372",
        results=[{"host": "DESKTOP-BRUCE", "user": "bwayne"}],
    )
    out = await enrich_alert_from_splunk(handoff, test_settings)
    assert out["enrichment_source"] == "inline_results"
    assert out["splunk_results"][0]["user"] == "bwayne"


@pytest.mark.asyncio
async def test_enrich_prefers_splunk_rest_over_single_webhook_row() -> None:
    settings = Settings(
        splunk_mgmt_url="https://127.0.0.1:8089",
        splunk_username="admin",
        splunk_password="secret",
        splunk_verify_ssl=False,
    )
    sid = "scheduler__admin__search__RMD5379db7c923f8a3ce_at_1780871040_929"
    handoff = SplunkAlertIngest(
        sid=sid,
        search_name="New TesT",
        results=[{"Computer": "inline-only", "User": "bob"}],
    )
    rest_rows = [
        {"Computer": "we8105desk", "User": "bob", "_time": "2018-08-24 21:18:41"},
        {"Computer": "we8105desk", "User": "bob", "_time": "2018-08-24 21:18:50"},
    ]
    client = MagicMock()
    client.login = AsyncMock(return_value="sk")
    client.get_job = AsyncMock(return_value={"entry": [{"content": {"dispatchState": "DONE"}}]})
    client.fetch_all_results = AsyncMock(return_value=rest_rows)

    with patch("services.alert.alert_pipeline.SplunkRestClient", return_value=client):
        out = await enrich_alert_from_splunk(handoff, settings)

    assert out["enrichment_source"] == "splunk_rest"
    assert out["splunk_results_row_count"] == 2
    assert out["splunk_results"][0]["Computer"] == "we8105desk"
    client.fetch_all_results.assert_awaited_once_with(sid, "sk")
