"""SOC analysis (offline inventory, LangGraph fallback when LiteLLM unavailable)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings, get_settings
from main import app
from services.soc_analysis import run_analysis
from services.soc_analysis.soc_analysis_batch import merge_normalized_for_row


@pytest.fixture
def client_analysis_fallback(test_settings: Settings, force_soc_analysis_langgraph_fallback):
    def _override() -> Settings:
        return test_settings

    app.dependency_overrides[get_settings] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


_USERS = [{"user_id": "jdoe", "risk_score": "3", "department": "IT"}]
_ASSETS = [
    {
        "asset_id": "srv-web-01",
        "hostname": "web-prod-01",
        "ip": "10.0.0.5",
        "criticality": "high",
        "risk_score": "4",
    }
]
_RELATIONSHIPS: list = []


def test_verdict_implies_false_positive() -> None:
    from services.soc_analysis.soc_verdict import verdict_implies_false_positive

    assert verdict_implies_false_positive("likely_benign") is True
    assert verdict_implies_false_positive("false_positive") is True
    assert verdict_implies_false_positive("FP") is True
    assert verdict_implies_false_positive("needs_investigation") is False
    assert verdict_implies_false_positive("true_positive") is False
    assert verdict_implies_false_positive("insufficient_data") is False


def test_investigation_questions_for_verdict_filters_fp() -> None:
    from services.investigation.investigation_questions_spl import investigation_questions_for_verdict

    qs = ["Check parent of cmd.exe"]
    items = investigation_questions_for_verdict("needs_investigation", qs, normalized={"host": "h1"})
    assert len(items) == 1
    assert items[0].question == qs[0]
    assert items[0].spl
    assert investigation_questions_for_verdict("likely_benign", qs) == []
    assert investigation_questions_for_verdict("false_positive", ["x"]) == []


def test_investigation_questions_max_default_three(test_settings) -> None:
    from config import investigation_questions_max
    from services.investigation.investigation_questions_spl import investigation_questions_for_verdict
    from services.soc_analysis.soc_verdict import sanitize_investigation_questions

    assert investigation_questions_max(test_settings) == 3
    many = [f"Question {i}?" for i in range(10)]
    strings = sanitize_investigation_questions(many)
    assert len(strings) == 3
    items = investigation_questions_for_verdict(
        "needs_investigation", many, settings=test_settings, normalized={}
    )
    assert len(items) == 3


@pytest.mark.asyncio
async def test_run_analysis_fallback_unit(
    test_settings: Settings, force_soc_analysis_langgraph_fallback
) -> None:
    s = test_settings
    body_dict = {
        "normalized": {"host": "web-prod-01"},
        "search_name": "test-alert",
    }
    from models.analysis import AnalysisRunRequest

    out = await run_analysis(
        s,
        AnalysisRunRequest(**body_dict),
        users=_USERS,
        assets=_ASSETS,
        relationships=_RELATIONSHIPS,
    )
    assert out.judge.verdict == "needs_investigation"
    assert out.enrichment.resolved_asset_id == "srv-web-01"
    assert out.hunter.splunk_search_suggestions
    assert out.framework_mapping
    assert any("mitre" in (x.framework or "").lower() for x in out.framework_mapping)
    assert any("kill chain" in (x.framework or "").lower() for x in out.framework_mapping)
    assert out.investigation_questions
    assert any(
        "host" in item.question.lower() or "web-prod" in item.question.lower()
        for item in out.investigation_questions
    )
    assert all(item.spl for item in out.investigation_questions)
    assert out.evidence_chain is not None
    assert out.evidence_chain.request.get("search_name") == "test-alert"
    assert out.evidence_chain.decision.get("verdict") == out.judge.verdict
    assert out.evidence_chain.reasoning_path.get("analysis_path") == "langgraph_fallback"
    assert out.evidence_chain.data_sources.get("splunk_results_row_count") == 0


def test_analysis_run_api_offline(client_analysis_fallback: TestClient) -> None:
    r = client_analysis_fallback.post(
        "/api/v1/analysis/run",
        json={
            "normalized": {"host": "web-prod-01"},
            "search_name": "n",
            "users": _USERS,
            "assets": _ASSETS,
            "relationships": _RELATIONSHIPS,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["judge"]["verdict"] == "needs_investigation"
    assert data["enrichment"]["resolved_asset_id"] == "srv-web-01"
    assert data["hunter"]["splunk_search_suggestions"]
    assert data.get("investigation_questions")
    assert data.get("evidence_chain")
    assert data["evidence_chain"]["decision"]["verdict"] == data["judge"]["verdict"]
    assert data["evidence_chain"]["reasoning_path"]["analysis_path"] == "langgraph_fallback"


def test_soc_analysis_prompts_follow_thinking_soc_v2_style() -> None:
    from services.soc_analysis.soc_analysis_prompts import (
        load_admin_org_gap_system_prompt,
        load_defender_system_prompt,
        load_framework_mapping_system_prompt,
        load_hunter_system_prompt,
        load_investigation_questions_system_prompt,
        load_judge_system_prompt,
    )

    for loader in (
        load_defender_system_prompt,
        load_hunter_system_prompt,
        load_judge_system_prompt,
        load_framework_mapping_system_prompt,
        load_investigation_questions_system_prompt,
        load_admin_org_gap_system_prompt,
    ):
        text = loader()
        assert "Your ENTIRE response MUST be a single, valid JSON object" in text
        assert "no markdown code fence" in text
        assert "{{" in text and "}}" in text


def test_analysis_partial_inventory_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/v1/analysis/run",
        json={"normalized": {}, "users": [], "assets": None, "relationships": None},
    )
    assert r.status_code == 400


def test_merge_normalized_for_row_skips_mv() -> None:
    base = {"host": "h1", "x": "1"}
    row = {"host": "h2", "__mv_host": "mv", "user": "u1"}
    m = merge_normalized_for_row(base, row)
    assert m["host"] == "h2"
    assert m["user"] == "u1"
    assert "__mv_host" not in m


def test_extract_iocs_smoke() -> None:
    from services.threat_intel.virustotal import extract_iocs

    normalized = {
        "host": "web-prod-01",
        "url": "http://example.com/a",
        "hash": "44d88612fea8a8f36de82e1278abb02f",  # md5 (eicar)
        "ip": "8.8.8.8",
        "domain": "example.com",
        "src_ip": "10.0.0.1",
        "dest_ip": "192.168.50.2",
    }
    out = extract_iocs(normalized, [], max_iocs=8)
    assert out["file_hashes"]
    assert out["ips"]
    assert "8.8.8.8" in out["ips"]
    assert "10.0.0.1" not in out["ips"]
    assert "192.168.50.2" not in out["ips"]
    assert out["domains"]
    assert out["urls"]


def test_extract_iocs_public_ip_from_ip_field_regex() -> None:
    from services.threat_intel.virustotal import extract_iocs

    out = extract_iocs(
        {"dest_ip": "noise 10.0.0.5 172.16.0.1 contact 1.1.1.1 done"},
        [],
        max_iocs=8,
    )
    assert "1.1.1.1" in out["ips"]
    assert "10.0.0.5" not in out["ips"]
    assert "172.16.0.1" not in out["ips"]


def test_extract_iocs_ignores_unscoped_raw_field() -> None:
    from services.threat_intel.virustotal import extract_iocs

    out = extract_iocs(
        {},
        [{"_raw": "noise 10.0.0.5 contact 1.1.1.1 done"}],
        max_iocs=8,
    )
    assert out["ips"] == []


@pytest.mark.asyncio
async def test_run_analysis_batch_by_sid_unit(test_settings: Settings) -> None:
    from models.analysis import AnalysisBatchBySidRequest
    from services.soc_analysis.soc_analysis_batch import run_analysis_batch_by_sid

    s = test_settings

    async def _enrich(*args, **kwargs):
        return {
            "splunk_results": [
                {"host": "web-prod-01", "user": "a"},
                {"host": "web-prod-01", "user": "b"},
            ],
        }

    body = AnalysisBatchBySidRequest(sid="test-sid-1", search_name="n", normalized={})
    with (
        patch("services.soc_analysis.soc_analysis_batch.enrich_alert_from_splunk", new_callable=AsyncMock) as m,
        patch(
            "services.soc_analysis.runner.run_soc_analysis_langgraph",
            new_callable=AsyncMock,
        ) as lg,
    ):
        lg.side_effect = RuntimeError("test: LLM unavailable")
        m.side_effect = _enrich
        out = await run_analysis_batch_by_sid(
            s,
            body,
            users=_USERS,
            assets=_ASSETS,
            relationships=_RELATIONSHIPS,
        )
    assert out.sid == "test-sid-1"
    assert out.splunk_results_row_count == 2
    assert out.analyzed_row_count == 2
    assert len(out.rows) == 2
    assert out.rows[0].ok and out.rows[0].result
    assert out.rows[0].result.enrichment.resolved_asset_id == "srv-web-01"
    assert out.rows[1].ok and out.rows[1].result
    assert out.rows[0].row_index == 0
    assert out.rows[1].row_index == 1


@pytest.mark.asyncio
async def test_run_analysis_batch_by_sid_uses_storage_sid_suffix(test_settings: Settings) -> None:
    from models.analysis import AnalysisBatchBySidRequest
    from services.soc_analysis.soc_analysis_batch import run_analysis_batch_by_sid

    captured_sids: list[str] = []

    async def _enrich(*args, **kwargs):
        return {
            "splunk_results": [
                {"host": "web-prod-01", "user": "a"},
                {"host": "web-prod-01", "user": "b"},
            ],
        }

    async def _run_analysis(settings, body, **kwargs):
        captured_sids.append(body.sid)
        from services.soc_analysis.runner import build_fallback_soc_result
        from services.soc_analysis.soc_analysis_risk import build_risk_context
        from models.enrichment import EnrichmentResult
        from services.alert.alert_identity import enrich_from_inventory

        enrichment = enrich_from_inventory(body.normalized, _USERS, _ASSETS, _RELATIONSHIPS)
        risk = build_risk_context(enrichment, None, None)
        return build_fallback_soc_result(
            enrichment, risk, body.normalized, body.search_name or "", body.splunk_results or []
        )

    body = AnalysisBatchBySidRequest(sid="test-sid-1", search_name="n", normalized={})
    with (
        patch("services.soc_analysis.soc_analysis_batch.enrich_alert_from_splunk", new_callable=AsyncMock) as m,
        patch("services.soc_analysis.soc_analysis_batch.run_analysis", new_callable=AsyncMock) as run_m,
    ):
        m.side_effect = _enrich
        run_m.side_effect = _run_analysis
        await run_analysis_batch_by_sid(
            test_settings,
            body,
            users=_USERS,
            assets=_ASSETS,
            relationships=_RELATIONSHIPS,
        )

    assert captured_sids == ["test-sid-1-1", "test-sid-1-2"]


@pytest.mark.asyncio
async def test_run_analysis_batch_respects_max_rows(test_settings: Settings) -> None:
    from models.analysis import AnalysisBatchBySidRequest
    from services.soc_analysis.soc_analysis_batch import run_analysis_batch_by_sid

    s = test_settings

    async def _enrich(*args, **kwargs):
        return {"splunk_results": [{"host": "web-prod-01"}, {"host": "web-prod-01"}, {"host": "web-prod-01"}]}

    body = AnalysisBatchBySidRequest(sid="sid", max_rows=2)
    with (
        patch("services.soc_analysis.soc_analysis_batch.enrich_alert_from_splunk", new_callable=AsyncMock) as m,
        patch(
            "services.soc_analysis.runner.run_soc_analysis_langgraph",
            new_callable=AsyncMock,
        ) as lg,
    ):
        lg.side_effect = RuntimeError("test: LLM unavailable")
        m.side_effect = _enrich
        out = await run_analysis_batch_by_sid(
            s,
            body,
            users=_USERS,
            assets=_ASSETS,
            relationships=_RELATIONSHIPS,
        )
    assert out.splunk_results_row_count == 3
    assert out.analyzed_row_count == 2
    assert len(out.rows) == 2


def test_analysis_run_by_sid_api_offline(client_analysis_fallback: TestClient) -> None:
    async def _enrich(*args, **kwargs):
        return {"splunk_results": [{"host": "web-prod-01"}]}

    with patch("services.soc_analysis.soc_analysis_batch.enrich_alert_from_splunk", new_callable=AsyncMock) as m:
        m.side_effect = _enrich
        r = client_analysis_fallback.post(
            "/api/v1/analysis/run-by-sid",
            json={
                "sid": "job-123",
                "search_name": "n",
                "users": _USERS,
                "assets": _ASSETS,
                "relationships": _RELATIONSHIPS,
            },
        )
    assert r.status_code == 200
    data = r.json()
    assert data["sid"] == "job-123"
    assert data["splunk_results_row_count"] == 1
    assert data["analyzed_row_count"] == 1
    assert data["rows"][0]["ok"] is True
    assert data["rows"][0]["result"]["judge"]["verdict"] == "needs_investigation"
