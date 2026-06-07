"""PostgreSQL JSON store: JSONB serialization and submit/search helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import Settings
from models.analysis import (
    AnalysisRunRequest,
    HunterSection,
    JudgeVerdict,
    SocAnalysisResult,
)
from models.enrichment import EnrichmentResult


def _enrichment() -> EnrichmentResult:
    return EnrichmentResult(confidence="low", notes="test")
from services.splunk_json_store import (
    _jsonb_param,
    get_stored_event_by_id,
    persist_soc_investigation_phases,
    pg as pg_store,
    search_stored_events,
    splunk_store_configured,
    submit_hec_event,
)


def _mock_pool_with_conn() -> tuple[MagicMock, AsyncMock]:
    conn = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = conn
    cm.__aexit__.return_value = None
    pool = MagicMock()
    pool.acquire.return_value = cm
    return pool, conn


def test_splunk_store_not_configured_without_postgres_dsn() -> None:
    s = Settings(tsoc_postgres_dsn=None)
    assert splunk_store_configured(s) is False


def test_splunk_store_configured_when_dsn_set() -> None:
    s = Settings(tsoc_postgres_dsn="postgresql://tsoc:tsoc@localhost:5432/tsoc")
    assert splunk_store_configured(s) is True


def test_jsonb_param_serializes_dict() -> None:
    raw = _jsonb_param({"tsoc_record_type": "soc_analysis", "nested": {"a": 1}})
    assert isinstance(raw, str)
    assert json.loads(raw)["tsoc_record_type"] == "soc_analysis"


def test_jsonb_param_passes_through_json_string() -> None:
    s = '{"x": 1}'
    assert _jsonb_param(s) is s


def test_jsonb_param_default_str_for_datetime() -> None:
    dt = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    raw = _jsonb_param({"t": dt})
    assert "2026-05-16" in raw


@pytest.mark.asyncio
async def test_submit_event_skips_when_store_not_configured() -> None:
    s = Settings(tsoc_postgres_dsn=None)
    ok = await submit_hec_event(s, {"tsoc_record_type": "test", "x": 1})
    assert ok is False


@pytest.mark.asyncio
async def test_submit_hec_event_binds_json_string_not_dict() -> None:
    pool, conn = _mock_pool_with_conn()
    pg_store._PG_POOL = pool
    event = {
        "tsoc_record_type": "soc_analysis",
        "sid": "sid-1",
        "search_name": "alert",
        "nested": {"k": 1},
    }
    s = Settings(tsoc_postgres_dsn="postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc")

    ok = await submit_hec_event(s, event)

    assert ok is True
    conn.execute.assert_awaited_once()
    args = conn.execute.await_args.args
    assert args[4] is None  # row_index column (optional)
    assert args[5] == _jsonb_param(event)
    assert isinstance(args[5], str)
    assert "::jsonb" in args[0]


@pytest.mark.asyncio
async def test_submit_hec_event_returns_false_on_execute_error() -> None:
    pool, conn = _mock_pool_with_conn()
    conn.execute.side_effect = RuntimeError("db down")
    pg_store._PG_POOL = pool
    s = Settings(tsoc_postgres_dsn="postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc")

    ok = await submit_hec_event(s, {"tsoc_record_type": "test", "sid": "s1"})

    assert ok is False


@pytest.mark.asyncio
async def test_search_stored_events_maps_rows() -> None:
    pool, conn = _mock_pool_with_conn()
    created = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    row = {
        "id": 7,
        "created_at": created,
        "tsoc_record_type": "soc_analysis",
        "sid": "sid-1",
        "search_name": "n",
        "row_index": 2,
        "payload": {"verdict": "needs_investigation"},
    }
    conn.fetch = AsyncMock(return_value=[row])
    pg_store._PG_POOL = pool
    s = Settings(tsoc_postgres_dsn="postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc")

    out = await search_stored_events(s, sid="sid-1", record_type="soc_analysis", limit=10)

    assert len(out) == 1
    assert out[0]["id"] == 7
    assert out[0]["created_at"] == created.isoformat()
    assert out[0]["row_index"] == 2
    assert out[0]["payload"]["verdict"] == "needs_investigation"
    conn.fetch.assert_awaited_once()
    assert "sid = $1" in conn.fetch.await_args.args[0]
    assert "tsoc_record_type = $2" in conn.fetch.await_args.args[0]


@pytest.mark.asyncio
async def test_search_stored_events_empty_when_not_configured() -> None:
    s = Settings(tsoc_postgres_dsn=None)
    assert await search_stored_events(s, sid="x") == []


@pytest.mark.asyncio
async def test_get_stored_event_by_id_maps_row() -> None:
    pool, conn = _mock_pool_with_conn()
    created = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    row = {
        "id": 42,
        "created_at": created,
        "tsoc_record_type": "soc_analysis",
        "sid": "sid-1",
        "search_name": "alert",
        "row_index": 0,
        "payload": {"analysis": {"summary": "ok"}},
    }
    conn.fetchrow = AsyncMock(return_value=row)
    pg_store._PG_POOL = pool
    s = Settings(tsoc_postgres_dsn="postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc")

    out = await get_stored_event_by_id(s, 42)

    assert out is not None
    assert out["id"] == 42
    assert out["payload"]["analysis"]["summary"] == "ok"
    conn.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_stored_event_by_id_returns_none_when_missing() -> None:
    pool, conn = _mock_pool_with_conn()
    conn.fetchrow = AsyncMock(return_value=None)
    pg_store._PG_POOL = pool
    s = Settings(tsoc_postgres_dsn="postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc")

    out = await get_stored_event_by_id(s, 999)

    assert out is None


@pytest.mark.asyncio
async def test_get_stored_event_by_id_none_when_not_configured() -> None:
    s = Settings(tsoc_postgres_dsn=None)
    assert await get_stored_event_by_id(s, 1) is None


@pytest.mark.asyncio
async def test_persist_soc_investigation_phases_submits_each_stage() -> None:
    s = Settings(tsoc_postgres_dsn="postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc")
    body = AnalysisRunRequest(
        sid="sid-phases",
        search_name="demo",
        normalized={"host": "web-01"},
        splunk_results=[{"host": "web-01"}],
    )
    result = SocAnalysisResult(
        defender="summary ok",
        hunter=HunterSection(
            narrative="hunt",
            splunk_search_suggestions=["index=main"],
        ),
        judge=JudgeVerdict(
            verdict="needs_investigation",
            priority="high",
            recommended_next_step="investigate",
            rationale="test",
        ),
        enrichment=_enrichment(),
        framework_mapping=[],
        investigation_questions=[{"question": "q1", "spl": "index=* earliest=-24h | head 20"}],
        risk_context="low",
    )
    with patch(
        "services.splunk_json_store.pg.submit_hec_event", new_callable=AsyncMock
    ) as submit:
        await persist_soc_investigation_phases(s, body, result)

    assert submit.await_count >= 9
    types = {c.args[1]["tsoc_record_type"] for c in submit.await_args_list}
    assert "soc_investigation_threat_intel" not in types
    assert "soc_investigation_raw_alert" in types
    assert "soc_investigation_defender" in types
    assert "soc_investigation_judge" in types
    assert "soc_investigation_alert_fields" in types
    first = submit.await_args_list[0].args[1]
    assert first.get("row_index") == 0
    assert first.get("raw_alert", {}).get("sid") == "sid-phases"


@pytest.mark.asyncio
async def test_persist_soc_investigation_phases_includes_threat_intel_when_present() -> None:
    s = Settings(tsoc_postgres_dsn="postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc")
    body = AnalysisRunRequest(
        sid="sid-ti",
        search_name="demo",
        normalized={"src_ip": "203.0.113.1"},
        splunk_results=[],
    )
    result = SocAnalysisResult(
        defender="ok",
        hunter=HunterSection(narrative="h"),
        judge=JudgeVerdict(
            verdict="needs_investigation",
            priority="medium",
            recommended_next_step="review",
            rationale="test",
        ),
        enrichment=_enrichment(),
        risk_context="low",
        threat_intel={"virustotal": {"enabled": True, "ips": {"203.0.113.1": {"error": None}}}},
    )
    with patch(
        "services.splunk_json_store.pg.submit_hec_event", new_callable=AsyncMock
    ) as submit:
        await persist_soc_investigation_phases(s, body, result)

    types = {c.args[1]["tsoc_record_type"] for c in submit.await_args_list}
    assert "soc_investigation_threat_intel" in types


@pytest.mark.asyncio
async def test_persist_soc_investigation_phases_includes_evidence_chain_when_present() -> None:
    s = Settings(tsoc_postgres_dsn="postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc")
    body = AnalysisRunRequest(
        sid="sid-ec",
        search_name="demo",
        normalized={"host": "web-01"},
        splunk_results=[{"host": "web-01"}],
    )
    result = SocAnalysisResult(
        defender="ok",
        hunter=HunterSection(narrative="h"),
        judge=JudgeVerdict(
            verdict="needs_investigation",
            priority="medium",
            recommended_next_step="review",
            rationale="test",
        ),
        enrichment=_enrichment(),
        risk_context="low",
        evidence_chain={
            "request": {"sid": "sid-ec", "row_index": 0},
            "decision": {"verdict": "needs_investigation"},
        },
    )
    with patch(
        "services.splunk_json_store.pg.submit_hec_event", new_callable=AsyncMock
    ) as submit:
        await persist_soc_investigation_phases(s, body, result)

    phase_payloads = [c.args[1] for c in submit.await_args_list if c.args[1]["tsoc_record_type"] == "soc_investigation_evidence_chain"]
    assert len(phase_payloads) == 1
    assert phase_payloads[0]["content"]["request"]["sid"] == "sid-ec"
    assert phase_payloads[0]["content"]["decision"]["verdict"] == "needs_investigation"


@pytest.mark.asyncio
async def test_persist_soc_investigation_phases_skips_without_dsn() -> None:
    s = Settings(tsoc_postgres_dsn=None)
    body = AnalysisRunRequest(sid="s", normalized={})
    result = SocAnalysisResult(
        defender="",
        hunter=HunterSection(narrative=""),
        judge=JudgeVerdict(
            verdict="needs_investigation",
            priority="low",
            recommended_next_step="review",
            rationale="",
        ),
        enrichment=_enrichment(),
        risk_context="",
    )
    with patch(
        "services.splunk_json_store.pg.submit_hec_event", new_callable=AsyncMock
    ) as submit:
        await persist_soc_investigation_phases(s, body, result)
    submit.assert_not_awaited()


@pytest.mark.asyncio
async def test_persist_soc_analysis_audit_submits_row_index() -> None:
    s = Settings(tsoc_postgres_dsn="postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc")
    with patch(
        "services.splunk_json_store.pg.submit_hec_event", new_callable=AsyncMock
    ) as submit:
        from services.splunk_json_store import persist_soc_analysis_audit

        await persist_soc_analysis_audit(
            s,
            sid="sid-a",
            search_name="alert-x",
            row_index=2,
            raw_alert={"sid": "sid-a", "row_index": 2, "result_row": {"host": "h"}},
            analysis_input={"row_index": 2, "alert_fields": {"host": "h"}},
            analysis_output={"verdict": "needs_investigation"},
        )
    payload = submit.await_args.args[1]
    assert payload["tsoc_record_type"] == "soc_analysis_audit"
    assert payload["row_index"] == 2
    assert payload["raw_alert"]["result_row"]["host"] == "h"


@pytest.mark.asyncio
async def test_init_pg_connection_registers_jsonb_codec() -> None:
    conn = AsyncMock()
    await pg_store._init_pg_connection(conn)
    assert conn.set_type_codec.await_count == 2
    first = conn.set_type_codec.await_args_list[0].kwargs
    assert first["encoder"] is _jsonb_param
    assert first["schema"] == "pg_catalog"
