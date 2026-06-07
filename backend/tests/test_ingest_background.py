"""Ingest background triage tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from config import Settings, get_settings
from main import app
from models.handoff import SplunkAlertIngest


def test_splunk_ingest_async_accepted(mock_enrich_ok) -> None:
    def _override() -> Settings:
        return Settings(
            splunk_username="u",
            splunk_password="p",
            tsoc_postgres_dsn="",
            tsoc_ingest_auto_analyze=True,
        )

    app.dependency_overrides[get_settings] = _override
    with patch("main.init_store", new_callable=AsyncMock):
        with patch("api.routes.ingest.run_post_ingest", new_callable=AsyncMock) as m:
            with TestClient(app) as client:
                r = client.post(
                    "/api/v1/alerts/splunk-ingest",
                    json={"sid": "scheduler_123", "search_name": "demo", "result": {"host": "h1"}},
                )
    app.dependency_overrides.clear()
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "accepted"
    assert data["job_id"]


def test_splunk_ingest_rejects_config_query_params(mock_enrich_ok) -> None:
    def _override() -> Settings:
        return Settings(
            splunk_username="u",
            splunk_password="p",
            tsoc_postgres_dsn="",
            tsoc_ingest_auto_analyze=False,
        )

    app.dependency_overrides[get_settings] = _override
    with patch("main.init_store", new_callable=AsyncMock):
        with TestClient(app) as client:
            r = client.post(
                "/api/v1/alerts/splunk-ingest?auto_analyze=true&async_mode=true",
                json={"sid": "scheduler_123", "search_name": "demo", "result": {"host": "h1"}},
            )
    app.dependency_overrides.clear()
    assert r.status_code == 400
    assert "auto_analyze" in r.json()["forbidden_query_params"]


def test_run_post_ingest_calls_triage() -> None:
    async def _run() -> None:
        settings = Settings(
            tsoc_postgres_dsn="postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc",
            tsoc_ingest_auto_analyze_pipeline="triage",
        )
        handoff = SplunkAlertIngest(sid="s1", search_name="n1", normalized={"host": "x"})
        enriched = {"splunk_results_row_count": 1, "splunk_results": [{"host": "x"}]}
        with patch("services.alert.ingest_background.persist_splunk_ingest_summary", new_callable=AsyncMock):
            with patch("services.alert.ingest_background.run_agent_triage", new_callable=AsyncMock) as triage:
                from services.alert.ingest_background import run_post_ingest

                await run_post_ingest(settings, handoff, enriched, auto_analyze=True)
        triage.assert_awaited_once()

    asyncio.run(_run())
