"""Dashboard overview API tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings, get_settings
from main import app
from models.dashboard import DashboardOverview, DashboardKpis, SystemResources
from models.triage import TriageOutcome


@pytest.fixture
def client_dashboard(test_settings_with_ingest_token: Settings):
    def _override() -> Settings:
        return test_settings_with_ingest_token.model_copy(
            update={"tsoc_postgres_dsn": "postgresql://test"}
        )

    app.dependency_overrides[get_settings] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_dashboard_overview_503_without_postgres(client_with_token: TestClient) -> None:
    r = client_with_token.get(
        "/api/v1/dashboard/overview",
        headers={"Authorization": "Bearer expected-ingest-secret"},
    )
    assert r.status_code == 503


def test_dashboard_overview_ok(client_dashboard: TestClient) -> None:
    high = TriageOutcome(
        review_verdict="TRUE_POSITIVE",
        investigation_priority="critical",
        triage_score=90,
        confidence_score=0.9,
        priority_rationale="high",
        needs_human_review=True,
        source_track="security",
    )

    overview = DashboardOverview(
        generated_at="2026-05-18T12:00:00+00:00",
        postgres_configured=True,
        system_resources=SystemResources(
            hostname="test-host",
            cpu_percent=12.5,
            memory_percent=45.0,
            memory_used_bytes=4_000_000_000,
            memory_total_bytes=8_000_000_000,
        ),
        kpis=DashboardKpis(
            total_records=10,
            analyses_24h=2,
            needs_human_review=1,
            avg_triage_score=90.0,
            users=5,
            assets=3,
        ),
        activity_timeline=[
            {
                "date": "2026-05-18",
                "security": 2,
                "observability": 0,
                "correlation": 1,
                "other": 0,
            }
        ],
        record_type_counts=[{"type": "soc_analysis", "count": 8}],
        triage_by_verdict=[{"verdict": "TRUE_POSITIVE", "count": 1}],
        triage_by_priority=[{"priority": "critical", "count": 1}],
        track_split={"security": 1, "observability": 0},
        integrations={"postgres": True, "llm": False, "mcp": False, "neo4j": False},
        health_score=25,
        top_priority=[
            {
                "id": 1,
                "search_name": "alert-a",
                "triage_score": 90,
                "review_verdict": "TRUE_POSITIVE",
                "investigation_priority": "critical",
                "needs_human_review": True,
                "source_track": "security",
            }
        ],
    )

    async def fake_build(_settings: Settings) -> DashboardOverview:
        _ = high
        return overview

    with patch(
        "api.routes.dashboard.build_dashboard_overview",
        new_callable=AsyncMock,
        side_effect=fake_build,
    ):
        r = client_dashboard.get(
            "/api/v1/dashboard/overview",
            headers={"Authorization": "Bearer expected-ingest-secret"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["postgres_configured"] is True
    assert body["kpis"]["total_records"] == 10
    assert body["top_priority"][0]["search_name"] == "alert-a"
    assert body["health_score"] == 25
    assert body["integrations"]["neo4j"] is False
    assert body["system_resources"]["hostname"] == "test-host"
    assert body["system_resources"]["cpu_percent"] == 12.5
