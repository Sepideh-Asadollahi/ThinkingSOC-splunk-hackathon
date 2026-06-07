"""Admin org GAP suggestion (fallback + API)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings, get_settings
from main import app
from models.admin_org import AdminOrgGapSuggestRequest
from models.analysis import AnalysisRunRequest
from services.soc_analysis.admin_org_gap import (
    attach_admin_org_gap,
    build_admin_org_gap_request,
    rule_based_admin_org_gap,
    suggest_admin_org_gap,
)
from services.soc_analysis import run_analysis


@pytest.mark.asyncio
async def test_suggest_admin_org_gap_fallback_no_identity(test_settings: Settings) -> None:
    s = test_settings
    body = AdminOrgGapSuggestRequest(
        normalized={"host": "srv1"},
        sid="sid-1",
        search_name="my-alert",
        enrichment={"resolved_asset_id": None},
    )
    out = await suggest_admin_org_gap(s, body)
    assert out.should_suggest_question is True
    assert out.question_for_admin
    assert "my-alert" in out.question_for_admin


@pytest.mark.asyncio
async def test_suggest_admin_org_gap_fallback_with_asset(test_settings: Settings) -> None:
    s = test_settings
    body = AdminOrgGapSuggestRequest(
        normalized={"host": "srv1"},
        enrichment={"resolved_asset_id": "a-1"},
    )
    out = await suggest_admin_org_gap(s, body)
    assert out.should_suggest_question is False


@pytest.mark.asyncio
async def test_rule_based_osk_gap_even_when_asset_linked() -> None:
    body = AdminOrgGapSuggestRequest(
        normalized={
            "host": "we8105desk",
            "Image": r"C:\Windows\System32\osk.exe",
            "ParentImage": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            "signature_id": "T1218",
        },
        sid="sid-osk",
        search_name="Suspicious Process - osk.exe Sysmon EID 1 (botsv1)",
        enrichment={"resolved_asset_id": "botsv1-we8105desk", "resolved_user_id": "SYSTEM"},
        inventory_asset={
            "asset_id": "botsv1-we8105desk",
            "hostname": "we8105desk",
            "description": "BOTS v1 workstation",
        },
    )
    out = rule_based_admin_org_gap(body)
    assert out is not None
    assert out.should_suggest_question is True
    assert "osk.exe" in out.question_for_admin.lower()
    assert "we8105desk" in out.question_for_admin


@pytest.mark.asyncio
async def test_suggest_admin_org_gap_fallback_osk_with_asset(test_settings: Settings) -> None:
    s = test_settings
    body = AdminOrgGapSuggestRequest(
        normalized={
            "host": "we8105desk",
            "Image": r"C:\Windows\System32\osk.exe",
            "ParentCommandLine": "powershell.exe -File C:\\Users\\Public\\invoke.ps1",
        },
        enrichment={"resolved_asset_id": "botsv1-we8105desk"},
        inventory_asset={"hostname": "we8105desk"},
    )
    out = await suggest_admin_org_gap(s, body)
    assert out.should_suggest_question is True
    assert "osk.exe" in out.question_for_admin.lower()


@pytest.fixture
def client_admin_org_fallback(test_settings: Settings):
    def _override() -> Settings:
        return test_settings

    app.dependency_overrides[get_settings] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_build_admin_org_gap_request_from_soc_result(test_settings: Settings) -> None:
    from models.analysis import HunterSection, JudgeVerdict, SocAnalysisResult
    from models.enrichment import EnrichmentResult

    s = test_settings
    body = AnalysisRunRequest(
        normalized={"host": "unknown-host"},
        sid="sid-gap",
        search_name="gap-search",
    )
    enrichment = EnrichmentResult(
        confidence="low",
        notes="no match",
        resolved_asset_id=None,
        resolved_user_id=None,
    )
    result = SocAnalysisResult(
        defender="defender notes",
        hunter=HunterSection(narrative="hunter narrative", splunk_search_suggestions=[]),
        judge=JudgeVerdict(
            verdict="needs_investigation",
            priority="high",
            recommended_next_step="review",
            rationale="judge rationale",
        ),
        enrichment=enrichment,
        risk_context="medium risk",
    )
    gap_req = build_admin_org_gap_request(body, result)
    assert gap_req.sid == "sid-gap"
    assert gap_req.defender_text == "defender notes"
    assert gap_req.hunter_text == "hunter narrative"
    assert gap_req.judge_verdict == "needs_investigation"

    with patch(
        "services.soc_analysis.admin_org_gap.persist_admin_org_gap_to_splunk",
        new_callable=AsyncMock,
    ) as persist:
        attached = await attach_admin_org_gap(s, body, result)
    assert attached.admin_org_gap is not None
    assert attached.admin_org_gap.should_suggest_question is True
    persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_analysis_attaches_admin_org_gap_weak_identity(
    test_settings: Settings, force_soc_analysis_langgraph_fallback
) -> None:
    s = test_settings
    with patch(
        "services.soc_analysis.admin_org_gap.persist_admin_org_gap_to_splunk",
        new_callable=AsyncMock,
    ):
        out = await run_analysis(
            s,
            AnalysisRunRequest(
                normalized={"host": "unmatched-host-xyz"},
                search_name="weak-identity-alert",
                sid="sid-weak",
            ),
            users=[],
            assets=[],
            relationships=[],
        )
    assert out.admin_org_gap is not None
    assert out.admin_org_gap.should_suggest_question is True
    assert out.admin_org_gap.question_for_admin


@pytest.mark.asyncio
async def test_run_analysis_langgraph_attaches_admin_org_gap(test_settings: Settings) -> None:
    """Admin-org GAP must run on the LLM path when LangGraph succeeds."""
    from models.analysis import HunterSection, JudgeVerdict, SocAnalysisResult
    from models.enrichment import EnrichmentResult

    s = test_settings
    mock_result = SocAnalysisResult(
        defender="contain",
        hunter=HunterSection(narrative="hunt", splunk_search_suggestions=[]),
        judge=JudgeVerdict(
            verdict="needs_investigation",
            priority="high",
            recommended_next_step="isolate",
            rationale="test",
        ),
        enrichment=EnrichmentResult(
            confidence="high",
            notes="ok",
            resolved_asset_id="botsv1-we8105desk",
            resolved_user_id="SYSTEM",
        ),
        risk_context="high",
    )
    assets = [
        {
            "asset_id": "botsv1-we8105desk",
            "hostname": "we8105desk",
            "criticality": "critical",
            "risk_score": "8",
        }
    ]
    with (
        patch(
            "services.soc_analysis.runner.run_soc_analysis_langgraph",
            new_callable=AsyncMock,
            return_value={},
        ),
        patch(
            "services.soc_analysis.runner.assemble_from_langgraph",
            new_callable=AsyncMock,
            return_value=mock_result,
        ),
        patch(
            "services.soc_analysis.admin_org_gap.persist_admin_org_gap_to_splunk",
            new_callable=AsyncMock,
        ),
        patch("services.soc_analysis.runner._persist_analysis_bundle", new_callable=AsyncMock),
        patch("services.soc_analysis.runner.upsert_analysis_document", new_callable=AsyncMock),
        patch("services.soc_analysis.runner.find_similar_alerts", new_callable=AsyncMock) as sim,
    ):
        from services.soc_rag.models import SimilarAlertContext

        sim.return_value = SimilarAlertContext(similar_alerts=[], retrieval_notes="")
        out = await run_analysis(
            s,
            AnalysisRunRequest(
                normalized={
                    "host": "we8105desk",
                    "Image": r"C:\Windows\System32\osk.exe",
                    "ParentImage": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                },
                search_name="Suspicious Process - osk.exe Sysmon EID 1 (botsv1)",
                sid="sid-llm-gap",
            ),
            users=[],
            assets=assets,
            relationships=[],
        )
    assert out.admin_org_gap is not None
    assert out.admin_org_gap.should_suggest_question is True
    assert out.admin_org_gap.question_for_admin


@pytest.mark.asyncio
async def test_run_analysis_admin_org_gap_no_question_when_asset_linked(
    test_settings: Settings, force_soc_analysis_langgraph_fallback
) -> None:
    s = test_settings
    assets = [
        {
            "asset_id": "srv-web-01",
            "hostname": "web-prod-01",
            "ip": "10.0.0.5",
            "criticality": "high",
            "risk_score": "4",
        }
    ]
    with patch(
        "services.soc_analysis.admin_org_gap.persist_admin_org_gap_to_splunk",
        new_callable=AsyncMock,
    ):
        out = await run_analysis(
            s,
            AnalysisRunRequest(
                normalized={"host": "web-prod-01"},
                search_name="linked-alert",
            ),
            users=[],
            assets=assets,
            relationships=[],
        )
    assert out.admin_org_gap is not None
    assert out.admin_org_gap.should_suggest_question is False


@pytest.mark.asyncio
async def test_persist_soc_analysis_includes_admin_org_gap(test_settings: Settings) -> None:
    from models.analysis import HunterSection, JudgeVerdict, SocAnalysisResult
    from models.enrichment import EnrichmentResult
    from services.splunk_json_store import persist_soc_analysis_to_splunk

    s = test_settings.model_copy(
        update={"tsoc_postgres_dsn": "postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc"}
    )
    body = AnalysisRunRequest(sid="sid-store", search_name="s", normalized={"host": "h"})
    enrichment = EnrichmentResult(confidence="low", notes="test")
    result = SocAnalysisResult(
        defender="d",
        hunter=HunterSection(narrative="h"),
        judge=JudgeVerdict(
            verdict="needs_investigation",
            priority="low",
            recommended_next_step="review",
            rationale="r",
        ),
        enrichment=enrichment,
        risk_context="low",
        admin_org_gap=await suggest_admin_org_gap(
            s,
            AdminOrgGapSuggestRequest(normalized={"host": "h"}, enrichment={"resolved_asset_id": None}),
        ),
    )
    with patch(
        "services.splunk_json_store.pg.submit_hec_event", new_callable=AsyncMock
    ) as submit:
        await persist_soc_analysis_to_splunk(s, body, result)
    payload = submit.await_args.args[1]
    assert payload["analysis"]["admin_org_gap"]["should_suggest_question"] is True


def test_admin_org_gap_suggest_api(client_admin_org_fallback: TestClient) -> None:
    r = client_admin_org_fallback.post(
        "/api/v1/admin-org/gap-suggest",
        json={"normalized": {"host": "h"}, "search_name": "s", "sid": "job1"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "should_suggest_question" in data
    assert "question_for_admin" in data
