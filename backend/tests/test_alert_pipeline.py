from __future__ import annotations

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
