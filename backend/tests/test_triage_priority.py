"""Triage priority scoring and queue helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings, get_settings
from main import app
from models.agentic_ops import AlertClassificationResult
from models.analysis import HunterSection, JudgeVerdict, SocAnalysisResult
from models.enrichment import EnrichmentResult
from models.observability import (
    DiagnoserSection,
    EntityResolution,
    ImpactContext,
    ObservabilityAnalysisResult,
    OpsJudgeVerdict,
    ResponderSection,
)
from services.triage.triage_priority import (
    compute_triage_from_soc,
    compute_triage_outcome,
    investigation_priority_from_score,
    map_judge_verdict_to_review,
    triage_from_stored_payload,
)


def _soc_result(
    *,
    verdict: str = "needs_investigation",
    priority: str = "high",
    confidence: str | None = "medium",
) -> SocAnalysisResult:
    return SocAnalysisResult(
        defender="contain",
        hunter=HunterSection(narrative="hunt", splunk_search_suggestions=[]),
        judge=JudgeVerdict(
            verdict=verdict,
            priority=priority,
            recommended_next_step="review",
            rationale="test",
            confidence=confidence,  # type: ignore[arg-type]
        ),
        enrichment=EnrichmentResult(
            confidence="high",
            notes="ok",
        ),
        risk_context="risk",
    )


def test_map_false_positive() -> None:
    assert map_judge_verdict_to_review("likely_benign") == "FALSE_POSITIVE"


def test_map_true_positive() -> None:
    assert map_judge_verdict_to_review("true_positive") == "TRUE_POSITIVE"


def test_low_confidence_tp_escalates_to_human_review() -> None:
    triage = compute_triage_from_soc(_soc_result(verdict="true_positive", confidence="low"))
    assert triage.review_verdict == "NEEDS_HUMAN_REVIEW"
    assert "low_confidence_conviction_gate" in triage.signals


def test_triage_includes_structured_report() -> None:
    triage = compute_triage_from_soc(_soc_result(verdict="needs_investigation", confidence="medium"))
    assert triage.report is not None
    assert triage.report.headline
    assert triage.report.why_verdict
    assert triage.report.why_priority
    assert triage.report.recommended_action
    assert len(triage.report.factors) >= 1


def test_high_confidence_fp_low_score() -> None:
    triage = compute_triage_from_soc(_soc_result(verdict="false_positive", confidence="high"))
    assert triage.review_verdict == "FALSE_POSITIVE"
    assert triage.triage_score < 40


def test_needs_human_routing_boosts_score() -> None:
    base = compute_triage_from_soc(_soc_result())
    boosted = compute_triage_from_soc(
        _soc_result(),
        classification=AlertClassificationResult(
            track="unknown",
            recommended_pipeline="manual_review",
            confidence=0.35,
            reason="ambiguous",
            needs_human_routing=True,
        ),
    )
    assert boosted.triage_score > base.triage_score
    assert boosted.needs_human_review is True


def test_investigation_priority_buckets() -> None:
    assert investigation_priority_from_score(85) == "critical"
    assert investigation_priority_from_score(65) == "high"
    assert investigation_priority_from_score(45) == "medium"
    assert investigation_priority_from_score(20) == "low"


def test_triage_from_stored_payload_recomputes() -> None:
    soc = _soc_result(verdict="true_positive", confidence="high")
    soc = soc.model_copy(update={"triage": compute_triage_from_soc(soc)})
    payload = {
        "tsoc_record_type": "soc_analysis",
        "analysis": soc.model_dump(mode="json"),
    }
    triage = triage_from_stored_payload(payload)
    assert triage is not None
    assert triage.review_verdict == "TRUE_POSITIVE"


def test_observability_track() -> None:
    triage = compute_triage_outcome(
        source_track="observability",
        verdict="needs_more_evidence",
        priority="high",
        confidence="low",
        impact_level="critical",
    )
    assert triage.source_track == "observability"
    assert triage.review_verdict == "NEEDS_HUMAN_REVIEW"


@pytest.fixture
def client_triage_queue(test_settings_with_ingest_token: Settings):
    def _override() -> Settings:
        return test_settings_with_ingest_token.model_copy(
            update={"tsoc_postgres_dsn": "postgresql://test"}
        )

    app.dependency_overrides[get_settings] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_triage_queue_sorts_by_score(client_triage_queue: TestClient) -> None:
    from models.triage import TriageOutcome

    high = TriageOutcome(
        review_verdict="TRUE_POSITIVE",
        investigation_priority="critical",
        triage_score=90,
        confidence_score=0.9,
        priority_rationale="high",
        needs_human_review=False,
        source_track="security",
    )
    low = TriageOutcome(
        review_verdict="FALSE_POSITIVE",
        investigation_priority="low",
        triage_score=10,
        confidence_score=0.9,
        priority_rationale="low",
        needs_human_review=False,
        source_track="security",
    )

    async def fake_search(_settings, **kwargs):
        if kwargs.get("record_type") != "soc_analysis":
            return []
        return [
            {
                "id": 1,
                "created_at": "2026-01-01T00:00:00",
                "tsoc_record_type": "soc_analysis",
                "sid": "sid-low",
                "search_name": "low",
                "row_index": 0,
                "payload": {"triage": low.model_dump(mode="json")},
            },
            {
                "id": 2,
                "created_at": "2026-01-02T00:00:00",
                "tsoc_record_type": "soc_analysis",
                "sid": "sid-high",
                "search_name": "high",
                "row_index": 0,
                "payload": {"triage": high.model_dump(mode="json")},
            },
        ]

    with patch(
        "services.triage.triage_queue.search_stored_events",
        new_callable=AsyncMock,
        side_effect=fake_search,
    ):
        r = client_triage_queue.get(
            "/api/v1/triage/queue",
            headers={"Authorization": "Bearer expected-ingest-secret"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert body["results"][0]["sid"] == "sid-high"
    assert body["results"][1]["sid"] == "sid-low"
