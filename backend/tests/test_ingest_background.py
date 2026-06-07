"""Ingest background triage tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from config import Settings, get_settings
from main import app
from models.handoff import SplunkAlertIngest


def test_splunk_ingest_async_buffered(mock_enrich_ok) -> None:
    """Default auto-analyze path buffers the row (one POST per row) and returns 202."""
    def _override() -> Settings:
        return Settings(
            splunk_username="u",
            splunk_password="p",
            tsoc_postgres_dsn="",
            tsoc_ingest_auto_analyze=True,
            tsoc_ingest_row_buffer=True,
        )

    app.dependency_overrides[get_settings] = _override
    with patch("main.init_store", new_callable=AsyncMock):
        with patch("api.routes.ingest.accumulate_ingest_row", new_callable=AsyncMock) as acc:
            acc.return_value = {"base_sid": "scheduler_123", "buffered_rows": 1, "added": 1, "duplicates": 0}
            with TestClient(app) as client:
                r = client.post(
                    "/api/v1/alerts/splunk-ingest",
                    json={"sid": "scheduler_123", "search_name": "demo", "result": {"host": "h1"}},
                )
    app.dependency_overrides.clear()
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "buffered"
    assert data["buffered_rows"] == 1
    acc.assert_awaited_once()


def test_splunk_ingest_async_accepted_when_buffer_disabled(mock_enrich_ok) -> None:
    """With the buffer disabled, the per-HTTP-request path still runs background triage."""
    def _override() -> Settings:
        return Settings(
            splunk_username="u",
            splunk_password="p",
            tsoc_postgres_dsn="",
            tsoc_ingest_auto_analyze=True,
            tsoc_ingest_row_buffer=False,
        )

    app.dependency_overrides[get_settings] = _override
    with patch("main.init_store", new_callable=AsyncMock):
        with patch("api.routes.ingest.run_post_ingest", new_callable=AsyncMock):
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
            with patch(
                "services.alert.ingest_background.run_triage_for_ingest",
                new_callable=AsyncMock,
            ) as triage:
                from services.alert.ingest_background import run_post_ingest

                await run_post_ingest(settings, handoff, enriched, auto_analyze=True)
        triage.assert_awaited_once()


def test_run_post_ingest_multi_row_uses_all_rows_triage() -> None:
    async def _run() -> None:
        settings = Settings(
            tsoc_postgres_dsn="postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc",
            tsoc_ingest_auto_analyze_pipeline="triage",
        )
        handoff = SplunkAlertIngest(sid="1780870386.6468", search_name="New TesT", normalized={"host": "x"})
        enriched = {
            "splunk_results_row_count": 2,
            "splunk_results": [
                {"host": "we8105desk", "User": "bob"},
                {"host": "we8105desk", "User": "bob", "_time": "2018-08-24 21:18:50"},
            ],
        }
        with patch("services.alert.ingest_background.persist_splunk_ingest_summary", new_callable=AsyncMock):
            with patch(
                "services.alert.ingest_background.run_agent_triage_all_rows",
                new_callable=AsyncMock,
                return_value=[],
            ) as triage:
                from services.alert.ingest_background import run_post_ingest

                await run_post_ingest(settings, handoff, enriched, auto_analyze=True)
        triage.assert_awaited_once()
        call_body = triage.await_args.args[1]
        assert call_body.sid == "1780870386.6468"
        assert len(call_body.splunk_results) == 2

    asyncio.run(_run())

    asyncio.run(_run())
