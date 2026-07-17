from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devtools import (
    AsyncTsocSdkClient,
    TsocApiError,
    TsocAuthError,
    TsocNotFoundError,
    TsocSdkClient,
    TsocSdkError,
    TsocTimeoutError,
)

_BASE = "http://127.0.0.1:9876"

_CLASSIFY_OK = {
    "track": "observability",
    "recommended_pipeline": "observability",
    "confidence": 0.9,
    "reason": "metrics pattern",
    "signals": ["cpu", "latency"],
    "secondary_track": None,
    "needs_human_routing": False,
}


def _ok_response(data: dict):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = data
    r.raise_for_status.return_value = None
    return r


def _runbook_json(runbook_id: str = "rb-1") -> dict:
    return {
        "runbook_id": runbook_id,
        "source_record_id": 0,
        "title": "Imported checks",
        "summary": "Portable checks",
        "applicable_search_name": "Suspicious Login",
        "source_verdict": "needs_investigation",
        "steps": [
            {
                "step_id": "step-1",
                "title": "Inspect",
                "intent": "Inspect authentication evidence",
                "expected_evidence": "Authentication rows",
                "stop_condition": "Stop without telemetry",
            }
        ],
        "decision_rule": "Escalate on corroboration",
        "limitations": [],
        "source_results": [],
        "status": "DRAFT",
        "model": "portable-import",
        "compile_duration_ms": 1,
        "created_at": "2026-07-14T10:00:00Z",
    }


def _http_error(status_code: int, text: str = "error"):
    import httpx

    req = httpx.Request("POST", f"{_BASE}/api/v1/classification/alert")
    res = httpx.Response(status_code=status_code, request=req, text=text)
    return httpx.HTTPStatusError(str(status_code), request=req, response=res)


# ---------------------------------------------------------------------------
# Sync client tests
# ---------------------------------------------------------------------------


def test_sdk_classify_typed_response() -> None:
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(_CLASSIFY_OK)
        out = client.classify_alert({"normalized": {"cpu": 95}})
    assert out.track == "observability"
    assert out.recommended_pipeline == "observability"


def test_sdk_auth_error_maps_401() -> None:
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value.raise_for_status.side_effect = _http_error(401, "unauthorized")
        m.return_value.text = "unauthorized"
        with pytest.raises(TsocAuthError):
            client.classify_alert({"normalized": {"cpu": 95}})


def test_sdk_api_error_maps_500() -> None:
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value.raise_for_status.side_effect = _http_error(500, "boom")
        m.return_value.text = "boom"
        with pytest.raises(TsocApiError):
            client.classify_alert({"normalized": {"cpu": 95}})


def test_sdk_not_found_error_maps_404() -> None:
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value.raise_for_status.side_effect = _http_error(404, "not found")
        m.return_value.text = "not found"
        with pytest.raises(TsocNotFoundError):
            client.classify_alert({"normalized": {}})


def test_sdk_timeout_raises_after_retries() -> None:
    import httpx

    client = TsocSdkClient(base_url=_BASE, max_retries=1, retry_backoff_seconds=0.0)
    with patch("httpx.Client.post") as m:
        m.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(TsocTimeoutError):
            client.classify_alert({"normalized": {}})
    assert m.call_count == 2


def test_sdk_retries_on_503_then_succeeds() -> None:
    fail_resp = MagicMock()
    fail_resp.raise_for_status.side_effect = _http_error(503)
    fail_resp.text = "unavailable"

    client = TsocSdkClient(base_url=_BASE, max_retries=1, retry_backoff_seconds=0.0)
    with patch("httpx.Client.post") as m:
        m.side_effect = [fail_resp, _ok_response(_CLASSIFY_OK)]
        out = client.classify_alert({"normalized": {"cpu": 95}})
    assert out.track == "observability"
    assert m.call_count == 2


def test_sdk_bearer_header_set() -> None:
    client = TsocSdkClient(base_url=_BASE, ingest_token="test-token")
    headers = client._headers()
    assert headers["Authorization"] == "Bearer test-token"


def test_sdk_no_token_empty_headers() -> None:
    client = TsocSdkClient(base_url=_BASE)
    assert client._headers() == {}


def test_sdk_mcp_status() -> None:
    data = {"connected": True, "saia_available": False}
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.return_value = _ok_response(data)
        result = client.mcp_status()
    assert result["connected"] is True
    assert result["saia_available"] is False


def test_sdk_mcp_generate_spl() -> None:
    data = {"source": "splunk_mcp_saia", "spl": "search index=main user=jdoe", "explanation": "finds user", "raw": None}
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.mcp_generate_spl({"query": "find jdoe logins"})
    assert out.source == "splunk_mcp_saia"
    assert "jdoe" in out.spl


def test_sdk_mcp_call_tool() -> None:
    data = {"tool_name": "splunk_run_query", "result": {"rows": [{"count": "42"}]}}
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.mcp_call_tool({"tool_name": "splunk_run_query", "arguments": {"search_query": "search index=main"}})
    assert out.tool_name == "splunk_run_query"
    assert out.result["rows"][0]["count"] == "42"


def test_sdk_run_analysis_by_sid() -> None:
    data = {"sid": "123.456", "search_name": "test", "splunk_results_row_count": 1, "analyzed_row_count": 1, "rows": []}
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.run_analysis_by_sid({"sid": "123.456"})
    assert out.sid == "123.456"
    assert out.splunk_results_row_count == 1


def test_sdk_search_events() -> None:
    data = {"count": 2, "results": [{"id": "a"}, {"id": "b"}]}
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.return_value = _ok_response(data)
        result = client.search_events(record_type="soc_analysis", limit=10)
    assert result["count"] == 2
    assert len(result["results"]) == 2


def test_sdk_compatible_runbook_targets() -> None:
    data = {
        "source_record_id": 10,
        "search_name": "Suspicious Login",
        "count": 1,
        "results": [
            {
                "record_id": 20,
                "search_name": "Suspicious Login",
                "created_at": None,
                "sid": "sid-20",
                "row_index": 0,
                "summary": "Compatible investigation",
                "review_verdict": "TRUE_POSITIVE",
            }
        ],
    }
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as request:
        request.return_value = _ok_response(data)
        result = client.compatible_runbook_targets(10, limit=8)

    assert result.results[0].record_id == 20
    assert request.call_args.kwargs["params"] == {"limit": 8}


def test_sdk_runbook_library_and_revision_methods() -> None:
    draft = _runbook_json()
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as request:
        request.return_value = _ok_response(
            {
                "count": 1,
                "alert_count": 1,
                "groups": [
                    {
                        "alert_name": "Suspicious Login",
                        "count": 1,
                        "runbooks": [{"draft": draft}],
                    }
                ],
            }
        )
        library = client.runbook_library(search_name="Suspicious Login")
    assert library.groups[0].runbooks[0].draft.runbook_id == "rb-1"
    assert request.call_args.kwargs["params"] == {"search_name": "Suspicious Login"}

    with patch("httpx.Client.patch") as request:
        request.return_value = _ok_response(_runbook_json("rb-2"))
        revised = client.revise_runbook(
            "rb-1",
            {
                "title": "Imported checks",
                "summary": "Portable checks",
                "applicable_search_name": "Suspicious Login",
                "steps": draft["steps"],
                "decision_rule": "Escalate on corroboration",
                "limitations": [],
                "verify_on_source": False,
            },
        )
    assert revised.runbook_id == "rb-2"


def test_sdk_get_event() -> None:
    data = {"id": 42, "tsoc_record_type": "soc_analysis", "payload": {}}
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.return_value = _ok_response(data)
        result = client.get_event(42)
    assert result["id"] == 42


def test_sdk_dashboard_overview() -> None:
    data = {
        "generated_at": "2026-05-27T00:00:00Z",
        "postgres_configured": True,
        "kpis": {"total_records": 100, "records_24h": 10, "analyses_24h": 5, "health_score": 95.0},
        "activity_timeline": [],
        "record_type_counts": [],
        "triage_by_verdict": [],
        "triage_by_priority": [],
        "track_split": {"security": 0, "observability": 0, "both": 0},
        "integrations": {"splunk_configured": True, "mcp_configured": False, "postgres_configured": True},
    }
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.return_value = _ok_response(data)
        out = client.dashboard_overview()
    assert out.postgres_configured is True
    assert out.kpis.total_records == 100


def test_sdk_route_analysis() -> None:
    data = {
        "track": "security",
        "classification": {**_CLASSIFY_OK, "track": "security", "recommended_pipeline": "security"},
        "security_result": None,
        "observability_result": None,
        "mcp_used": False,
    }
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.route_analysis({"normalized": {"host": "srv-01", "user": "jdoe"}})
    assert out.track == "security"
    assert out.mcp_used is False


def test_sdk_run_agent_triage() -> None:
    data = {
        "track": "security",
        "classification": {**_CLASSIFY_OK, "track": "security", "recommended_pipeline": "security"},
        "agent_summary": "Failed login for jdoe detected",
        "next_actions": ["check logs", "correlate IPs", "review user activity"],
        "mcp_used": False,
    }
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.run_agent_triage({"normalized": {"user": "jdoe"}})
    assert out.track == "security"
    assert "jdoe" in out.agent_summary
    assert len(out.next_actions) == 3


def test_sdk_suggest_spl() -> None:
    data = {
        "source": "rule_based",
        "root_cause_spl": {"spl": "search index=main host=web-prod-01 | stats count by user", "explanation": "test"},
    }
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.suggest_spl({"normalized": {"host": "web-prod-01"}})
    assert out.source == "rule_based"
    assert "stats count" in out.root_cause_spl.spl


def test_sdk_run_analysis() -> None:
    data = {
        "defender": "High severity alert",
        "hunter": {"narrative": "lateral movement suspected", "splunk_search_suggestions": []},
        "judge": {"verdict": "true_positive", "priority": "high", "recommended_next_step": "escalate", "rationale": "confirmed", "confidence": "high"},
        "investigation_questions": [],
        "enrichment": {"confidence": "high", "notes": "matched user jdoe"},
        "risk_context": "high risk user",
    }
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.run_analysis({"normalized": {"host": "srv-01", "user": "jdoe"}})
    assert out.judge.verdict == "true_positive"
    assert out.defender == "High severity alert"


def test_sdk_get_error_on_get_raises_not_found() -> None:
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.return_value.raise_for_status.side_effect = _http_error(404, "not found")
        m.return_value.text = "not found"
        with pytest.raises(TsocNotFoundError):
            client.get_event(999)


def test_sdk_get_error_on_get_raises_timeout() -> None:
    import httpx

    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(TsocTimeoutError):
            client.search_events(limit=5)


def test_sdk_post_raw_raises_auth_error() -> None:
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value.raise_for_status.side_effect = _http_error(403, "forbidden")
        m.return_value.text = "forbidden"
        with pytest.raises(TsocAuthError):
            client.add_analyst_action(1, {"action": "escalate"})


def test_sdk_error_hierarchy() -> None:
    assert issubclass(TsocAuthError, TsocSdkError)
    assert issubclass(TsocNotFoundError, TsocSdkError)
    assert issubclass(TsocTimeoutError, TsocSdkError)
    assert issubclass(TsocApiError, TsocSdkError)


def test_sdk_api_error_carries_context() -> None:
    err = TsocApiError("fail", status_code=502, response_text="bad gateway")
    assert err.status_code == 502
    assert err.response_text == "bad gateway"


# ---------------------------------------------------------------------------
# Async client tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_sdk_classify_typed_response() -> None:
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(_CLASSIFY_OK)
        out = await client.classify_alert({"normalized": {"cpu": 95}})
    assert out.track == "observability"
    assert out.confidence == 0.9


@pytest.mark.asyncio
async def test_async_sdk_auth_error() -> None:
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        resp = MagicMock()
        resp.raise_for_status.side_effect = _http_error(403, "forbidden")
        resp.text = "forbidden"
        m.return_value = resp
        with pytest.raises(TsocAuthError):
            await client.classify_alert({"normalized": {}})


@pytest.mark.asyncio
async def test_async_sdk_timeout_raises() -> None:
    import httpx

    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(TsocTimeoutError):
            await client.classify_alert({"normalized": {}})


@pytest.mark.asyncio
async def test_async_sdk_mcp_status() -> None:
    data = {"connected": True, "saia_available": True}
    client = AsyncTsocSdkClient(base_url=_BASE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        result = await client.mcp_status()
    assert result["connected"] is True


@pytest.mark.asyncio
async def test_async_sdk_mcp_generate_spl() -> None:
    data = {"source": "splunk_mcp_saia", "spl": "search index=main", "explanation": "test", "raw": None}
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        out = await client.mcp_generate_spl({"query": "show events"})
    assert out.source == "splunk_mcp_saia"


@pytest.mark.asyncio
async def test_async_sdk_mcp_call_tool() -> None:
    data = {"tool_name": "splunk_get_indexes", "result": ["main", "summary"]}
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        out = await client.mcp_call_tool({"tool_name": "splunk_get_indexes"})
    assert out.tool_name == "splunk_get_indexes"


@pytest.mark.asyncio
async def test_async_sdk_dashboard_overview() -> None:
    data = {
        "generated_at": "2026-05-27T00:00:00Z",
        "postgres_configured": True,
        "kpis": {"total_records": 50, "records_24h": 5, "analyses_24h": 2, "health_score": 80.0},
        "activity_timeline": [],
        "record_type_counts": [],
        "triage_by_verdict": [],
        "triage_by_priority": [],
        "track_split": {"security": 0, "observability": 0, "both": 0},
        "integrations": {"splunk_configured": True, "mcp_configured": False, "postgres_configured": True},
    }
    client = AsyncTsocSdkClient(base_url=_BASE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        out = await client.dashboard_overview()
    assert out.kpis.total_records == 50


@pytest.mark.asyncio
async def test_async_sdk_search_events() -> None:
    data = {"count": 1, "results": [{"id": "x"}]}
    client = AsyncTsocSdkClient(base_url=_BASE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        result = await client.search_events(limit=5)
    assert result["count"] == 1


@pytest.mark.asyncio
async def test_async_sdk_compatible_runbook_targets() -> None:
    data = {
        "source_record_id": 10,
        "search_name": "Suspicious Login",
        "count": 0,
        "results": [],
    }
    client = AsyncTsocSdkClient(base_url=_BASE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as request:
        request.return_value = _ok_response(data)
        result = await client.compatible_runbook_targets(10, limit=6)

    assert result.count == 0
    assert request.call_args.kwargs["params"] == {"limit": 6}


@pytest.mark.asyncio
async def test_async_sdk_runbook_export() -> None:
    data = {
        "schema_version": "thinking-soc.runbook-library/v1",
        "exported_at": "2026-07-14T10:00:00Z",
        "runbooks": [
            {
                "title": "Imported checks",
                "summary": "Portable checks",
                "applicable_search_name": "Suspicious Login",
                "steps": _runbook_json()["steps"],
                "decision_rule": "Escalate on corroboration",
                "limitations": [],
            }
        ],
    }
    client = AsyncTsocSdkClient(base_url=_BASE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as request:
        request.return_value = _ok_response(data)
        result = await client.export_runbooks(search_name="Suspicious Login")
    assert result.schema_version == "thinking-soc.runbook-library/v1"
    assert request.call_args.kwargs["params"] == {
        "search_name": "Suspicious Login",
    }


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_cli_classify_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "classify", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"normalized": {"cpu": 95}}),
        patch.object(TsocSdkClient, "classify_alert") as m_cls,
    ):
        m_cls.return_value = MagicMock(
            model_dump=MagicMock(return_value={"track": "observability", "confidence": 0.9})
        )
        main()
    captured = capsys.readouterr()
    assert '"track": "observability"' in captured.out


def test_cli_mcp_status_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "mcp-status"]),
        patch.object(TsocSdkClient, "mcp_status", return_value={"connected": True}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"connected": true' in captured.out


def test_cli_auth_error_exits() -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "classify", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"normalized": {}}),
        patch.object(TsocSdkClient, "classify_alert", side_effect=TsocAuthError("denied")),
        pytest.raises(SystemExit),
    ):
        main()


def test_cli_mcp_generate_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "mcp-generate", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"query": "find logins"}),
        patch.object(TsocSdkClient, "mcp_generate_spl") as m,
    ):
        m.return_value = MagicMock(
            model_dump=MagicMock(return_value={"source": "splunk_mcp_saia", "spl": "search index=main"})
        )
        main()
    captured = capsys.readouterr()
    assert '"source": "splunk_mcp_saia"' in captured.out


def test_cli_mcp_tool_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "mcp-tool", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"tool_name": "splunk_get_indexes"}),
        patch.object(TsocSdkClient, "mcp_call_tool") as m,
    ):
        m.return_value = MagicMock(
            model_dump=MagicMock(return_value={"tool_name": "splunk_get_indexes", "result": ["main"]})
        )
        main()
    captured = capsys.readouterr()
    assert '"tool_name": "splunk_get_indexes"' in captured.out


def test_cli_dashboard_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "dashboard"]),
        patch.object(TsocSdkClient, "dashboard_overview") as m,
    ):
        m.return_value = MagicMock(
            model_dump=MagicMock(return_value={"generated_at": "2026-05-27", "postgres_configured": True})
        )
        main()
    captured = capsys.readouterr()
    assert '"postgres_configured": true' in captured.out


def test_cli_run_by_sid_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "run-by-sid", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"sid": "123.456"}),
        patch.object(TsocSdkClient, "run_analysis_by_sid") as m,
    ):
        m.return_value = MagicMock(
            model_dump=MagicMock(return_value={"sid": "123.456", "analyzed_row_count": 1})
        )
        main()
    captured = capsys.readouterr()
    assert '"sid": "123.456"' in captured.out


def test_cli_route_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "route", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"normalized": {"user": "jdoe"}}),
        patch.object(TsocSdkClient, "route_analysis") as m,
    ):
        m.return_value = MagicMock(
            model_dump=MagicMock(return_value={"track": "security", "mcp_used": False})
        )
        main()
    captured = capsys.readouterr()
    assert '"track": "security"' in captured.out


def test_cli_agent_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "agent", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"normalized": {"user": "jdoe"}}),
        patch.object(TsocSdkClient, "run_agent_triage") as m,
    ):
        m.return_value = MagicMock(
            model_dump=MagicMock(return_value={"track": "security", "agent_summary": "test"})
        )
        main()
    captured = capsys.readouterr()
    assert '"agent_summary": "test"' in captured.out


def test_cli_spl_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "spl", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"normalized": {"host": "x"}}),
        patch.object(TsocSdkClient, "suggest_spl") as m,
    ):
        m.return_value = MagicMock(
            model_dump=MagicMock(return_value={"source": "rule_based", "root_cause_spl": {"spl": "search index=main"}})
        )
        main()
    captured = capsys.readouterr()
    assert '"source": "rule_based"' in captured.out


def test_cli_obs_by_sid_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "obs-by-sid", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"sid": "obs.456"}),
        patch.object(TsocSdkClient, "run_observability_by_sid") as m,
    ):
        m.return_value = MagicMock(
            model_dump=MagicMock(return_value={"sid": "obs.456", "analyzed_row_count": 5})
        )
        main()
    captured = capsys.readouterr()
    assert '"sid": "obs.456"' in captured.out


def test_cli_obs_run_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "obs-run", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"normalized": {"cpu": 95}}),
        patch.object(TsocSdkClient, "run_observability") as m,
    ):
        m.return_value = MagicMock(
            model_dump=MagicMock(return_value={"track": "observability", "summary": "ok"})
        )
        main()
    captured = capsys.readouterr()
    assert '"track": "observability"' in captured.out


def test_cli_soc_chat_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "soc-chat", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"messages": [{"role": "user", "content": "hi"}]}),
        patch.object(TsocSdkClient, "soc_chat") as m,
    ):
        m.return_value = MagicMock(
            model_dump=MagicMock(return_value={"answer": "hello", "citations": []})
        )
        main()
    captured = capsys.readouterr()
    assert '"answer": "hello"' in captured.out


def test_cli_chat_status_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "chat-status"]),
        patch.object(TsocSdkClient, "soc_chat_status", return_value={"enabled": True, "document_count": 10}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"enabled": true' in captured.out


def test_cli_triage_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "triage", "--track", "security", "--limit", "5"]),
        patch.object(TsocSdkClient, "triage_queue", return_value={"count": 1, "results": [{"id": 1}]}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"count": 1' in captured.out


def test_cli_timeline_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "timeline", "--record-id", "42"]),
        patch.object(TsocSdkClient, "investigation_timeline", return_value={"found": True, "steps": []}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"found": true' in captured.out


def test_cli_health_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "health"]),
        patch.object(TsocSdkClient, "health", return_value={"status": "ok"}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"status": "ok"' in captured.out


# ---------------------------------------------------------------------------
# New SDK method tests (sync)
# ---------------------------------------------------------------------------


def test_sdk_run_observability() -> None:
    data = {
        "track": "observability",
        "summary": "CPU spike detected",
        "entity_resolution": {"confidence": "high", "notes": "resolved via hostname"},
        "impact_context": {"impact_level": "high", "customer_impact": "degraded", "business_criticality": "high"},
        "diagnoser": {"root_cause_hypotheses": [], "followup_searches": []},
        "responder": {"recommended_actions": ["scale up"], "safety_notes": []},
        "ops_judge": {"verdict": "actionable", "priority": "high", "confidence": "high", "rationale": "test", "recommended_next_step": "scale"},
        "evidence_refs": [],
    }
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.run_observability({"normalized": {"cpu": 95}})
    assert out.track == "observability"
    assert out.ops_judge.verdict == "actionable"


def test_sdk_run_observability_by_sid() -> None:
    data = {"sid": "999.123", "search_name": "CPU", "splunk_results_row_count": 2, "analyzed_row_count": 2, "rows": []}
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.run_observability_by_sid({"sid": "999.123"})
    assert out.sid == "999.123"


def test_sdk_soc_chat() -> None:
    data = {"answer": "Based on the analysis...", "citations": [], "retrieval_backend": "postgres"}
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.soc_chat({"messages": [{"role": "user", "content": "what happened?"}]})
    assert "analysis" in out.answer


def test_sdk_soc_chat_status() -> None:
    data = {"enabled": True, "document_count": 42, "vector_enabled": True}
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.return_value = _ok_response(data)
        result = client.soc_chat_status()
    assert result["enabled"] is True
    assert result["document_count"] == 42


def test_sdk_investigation_timeline() -> None:
    data = {"found": True, "record_id": 42, "steps": [{"phase": "ingest"}, {"phase": "analysis"}]}
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.return_value = _ok_response(data)
        result = client.investigation_timeline(42)
    assert result["found"] is True
    assert len(result["steps"]) == 2


def test_sdk_analyst_actions() -> None:
    data = {"record_id": 10, "count": 1, "results": [{"action": "acknowledge"}]}
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.return_value = _ok_response(data)
        result = client.analyst_actions(10)
    assert result["count"] == 1


def test_sdk_add_analyst_action() -> None:
    data = {"record_id": 10, "saved": {"ok": True}, "latest": {"action": "escalate"}, "results": []}
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        result = client.add_analyst_action(10, {"action": "escalate", "note": "urgent"})
    assert result["saved"]["ok"] is True


def test_sdk_triage_queue() -> None:
    data = {"track": "all", "count": 3, "results": [{"id": 1}, {"id": 2}, {"id": 3}]}
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.return_value = _ok_response(data)
        result = client.triage_queue(track="security", limit=10)
    assert result["count"] == 3


def test_sdk_health() -> None:
    data = {"status": "ok"}
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.return_value = _ok_response(data)
        result = client.health()
    assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# New SDK method tests (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_sdk_route_analysis() -> None:
    data = {
        "track": "security",
        "classification": {**_CLASSIFY_OK, "track": "security", "recommended_pipeline": "security"},
        "mcp_used": True,
    }
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        out = await client.route_analysis({"normalized": {"user": "jdoe"}})
    assert out.track == "security"
    assert out.mcp_used is True


@pytest.mark.asyncio
async def test_async_sdk_run_agent_triage() -> None:
    data = {
        "track": "security",
        "classification": {**_CLASSIFY_OK, "track": "security", "recommended_pipeline": "security"},
        "agent_summary": "Auth failure",
        "next_actions": ["a", "b"],
        "mcp_used": False,
    }
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        out = await client.run_agent_triage({"normalized": {"user": "jdoe"}})
    assert out.agent_summary == "Auth failure"


@pytest.mark.asyncio
async def test_async_sdk_suggest_spl() -> None:
    data = {
        "source": "llm",
        "root_cause_spl": {"spl": "search index=main | head 10", "explanation": "test"},
    }
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        out = await client.suggest_spl({"normalized": {"host": "x"}})
    assert out.source == "llm"


@pytest.mark.asyncio
async def test_async_sdk_run_analysis() -> None:
    data = {
        "defender": "alert",
        "hunter": {"narrative": "test hypothesis", "splunk_search_suggestions": []},
        "judge": {"verdict": "false_positive", "priority": "low", "recommended_next_step": "close", "rationale": "ok", "confidence": "medium"},
        "investigation_questions": [],
        "enrichment": {"confidence": "low", "notes": "no match"},
        "risk_context": "low",
    }
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        out = await client.run_analysis({"normalized": {"host": "x"}})
    assert out.judge.verdict == "false_positive"


@pytest.mark.asyncio
async def test_async_sdk_run_analysis_by_sid() -> None:
    data = {"sid": "abc.789", "splunk_results_row_count": 5, "analyzed_row_count": 3, "rows": []}
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        out = await client.run_analysis_by_sid({"sid": "abc.789"})
    assert out.sid == "abc.789"
    assert out.analyzed_row_count == 3


@pytest.mark.asyncio
async def test_async_sdk_get_event() -> None:
    data = {"id": 7, "tsoc_record_type": "soc_analysis", "payload": {"k": "v"}}
    client = AsyncTsocSdkClient(base_url=_BASE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        result = await client.get_event(7)
    assert result["id"] == 7


@pytest.mark.asyncio
async def test_async_sdk_run_observability_by_sid() -> None:
    data = {"sid": "obs.456", "splunk_results_row_count": 10, "analyzed_row_count": 8, "rows": []}
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        out = await client.run_observability_by_sid({"sid": "obs.456"})
    assert out.sid == "obs.456"


@pytest.mark.asyncio
async def test_async_sdk_soc_chat_status() -> None:
    data = {"enabled": True, "document_count": 5, "default_retrieval": "postgres"}
    client = AsyncTsocSdkClient(base_url=_BASE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        result = await client.soc_chat_status()
    assert result["enabled"] is True


@pytest.mark.asyncio
async def test_async_sdk_analyst_actions() -> None:
    data = {"record_id": 5, "count": 2, "results": [{"action": "acknowledge"}, {"action": "escalate"}]}
    client = AsyncTsocSdkClient(base_url=_BASE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        result = await client.analyst_actions(5)
    assert result["count"] == 2


@pytest.mark.asyncio
async def test_async_sdk_add_analyst_action() -> None:
    data = {"record_id": 5, "saved": {"ok": True}, "latest": {"action": "escalate"}, "results": []}
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        result = await client.add_analyst_action(5, {"action": "escalate"})
    assert result["saved"]["ok"] is True


@pytest.mark.asyncio
async def test_async_sdk_run_observability() -> None:
    data = {
        "track": "observability",
        "summary": "test",
        "entity_resolution": {"confidence": "medium", "notes": "hostname match"},
        "impact_context": {"impact_level": "low", "customer_impact": "none", "business_criticality": "low"},
        "diagnoser": {"root_cause_hypotheses": [], "followup_searches": []},
        "responder": {"recommended_actions": [], "safety_notes": []},
        "ops_judge": {"verdict": "low_priority", "priority": "low", "confidence": "low", "rationale": "test", "recommended_next_step": "monitor"},
        "evidence_refs": [],
    }
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        out = await client.run_observability({"normalized": {"cpu": 50}})
    assert out.track == "observability"


@pytest.mark.asyncio
async def test_async_sdk_soc_chat() -> None:
    data = {"answer": "here is info", "citations": [], "retrieval_backend": "qdrant"}
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        out = await client.soc_chat({"messages": [{"role": "user", "content": "tell me"}]})
    assert out.retrieval_backend == "qdrant"


@pytest.mark.asyncio
async def test_async_sdk_triage_queue() -> None:
    data = {"count": 2, "results": [{"id": 1}, {"id": 2}]}
    client = AsyncTsocSdkClient(base_url=_BASE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        result = await client.triage_queue(limit=5)
    assert result["count"] == 2


@pytest.mark.asyncio
async def test_async_sdk_investigation_timeline() -> None:
    data = {"found": True, "steps": []}
    client = AsyncTsocSdkClient(base_url=_BASE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        result = await client.investigation_timeline(42)
    assert result["found"] is True


@pytest.mark.asyncio
async def test_async_sdk_health() -> None:
    data = {"status": "ok"}
    client = AsyncTsocSdkClient(base_url=_BASE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        result = await client.health()
    assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# Evaluate scoring tests
# ---------------------------------------------------------------------------


def test_evaluate_score_row_perfect() -> None:
    from devtools.evaluate import _score_row

    agent = {
        "track": "security",
        "classification": {"confidence": 0.85},
        "next_actions": ["a", "b", "c"],
        "security_result": {"verdict": "true_positive"},
    }
    spl = {"root_cause_spl": {"spl": "search index=main host=web-prod-01 | stats count by user"}}
    score, details = _score_row("security", agent, spl)
    assert score == 100
    assert details["track_match"] is True
    assert details["confidence_ok"] is True
    assert details["actions_ok"] is True
    assert details["pipeline_output_ok"] is True
    assert details["spl_ok"] is True


def test_evaluate_score_row_wrong_track() -> None:
    from devtools.evaluate import _score_row

    agent = {
        "track": "observability",
        "classification": {"confidence": 0.85},
        "next_actions": ["a", "b", "c"],
        "security_result": None,
        "observability_result": {"impact": "high"},
    }
    spl = {"root_cause_spl": {"spl": "search index=main | stats count"}}
    score, details = _score_row("security", agent, spl)
    assert details["track_match"] is False
    assert score < 100


def test_evaluate_score_row_low_confidence() -> None:
    from devtools.evaluate import _score_row

    agent = {
        "track": "security",
        "classification": {"confidence": 0.3},
        "next_actions": ["a", "b", "c"],
        "security_result": {"verdict": "tp"},
    }
    spl = {"root_cause_spl": {"spl": "search index=main host=x | stats count by user"}}
    score, details = _score_row("security", agent, spl)
    assert details["confidence_ok"] is False
    assert score == 85


def test_evaluate_score_row_few_actions() -> None:
    from devtools.evaluate import _score_row

    agent = {
        "track": "security",
        "classification": {"confidence": 0.8},
        "next_actions": ["a"],
        "security_result": {"verdict": "tp"},
    }
    spl = {"root_cause_spl": {"spl": "search index=main host=x | stats count by user"}}
    score, details = _score_row("security", agent, spl)
    assert details["actions_ok"] is False
    assert score == 85


# ---------------------------------------------------------------------------
# New SDK methods (ingest, doctor, MCP wrappers, full investigation)
# ---------------------------------------------------------------------------


def test_workflows_build_doctor_report_all_ok() -> None:
    from devtools.workflows import build_doctor_report

    report = build_doctor_report(
        health={"status": "ok"},
        mcp_status={"configured": True, "connected": True, "saia_available": True},
        llm_status={"litellm_model": "gpt-4", "litellm_api_key_configured": True},
        soc_chat_status={"enabled": True, "document_count": 10},
        graph_health={"status": "ok", "neo4j": True, "postgres": True},
        inventory_status={"postgres_configured": True, "source": "postgresql"},
    )
    assert report["ok"] is True
    assert report["ready_for_demo"] is True
    assert report["checks"]["mcp"]["saia_available"] is True
    assert report["checks"]["graph"]["ok"] is True
    assert report["checks"]["inventory"]["ok"] is True


def test_workflows_build_doctor_report_backend_down() -> None:
    from devtools.workflows import build_doctor_report

    report = build_doctor_report(
        health={"status": "degraded"},
        mcp_status={"configured": False, "connected": False},
        llm_status={"litellm_model": None, "litellm_api_key_configured": False},
        soc_chat_status={"enabled": False},
    )
    assert report["ok"] is False
    assert report["ready_for_demo"] is False


def test_sdk_ingest_alert() -> None:
    data = {"ok": True, "status": "accepted", "job_id": "abc-123", "sid": "1749825600.1"}
    client = TsocSdkClient(base_url=_BASE, ingest_token="tok", max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        result = client.ingest_alert({"sid": "1749825600.1", "normalized": {"user": "jdoe"}})
    assert result["ok"] is True
    assert result["job_id"] == "abc-123"


def test_sdk_llm_status() -> None:
    data = {"litellm_model": "gpt-4", "litellm_api_key_configured": True}
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.return_value = _ok_response(data)
        result = client.llm_status()
    assert result["litellm_model"] == "gpt-4"


def test_sdk_doctor() -> None:
    client = TsocSdkClient(base_url=_BASE)
    with (
        patch.object(client, "health", return_value={"status": "ok"}),
        patch.object(client, "mcp_status", return_value={"configured": True, "connected": True, "saia_available": True}),
        patch.object(client, "llm_status", return_value={"litellm_model": "gpt-4", "litellm_api_key_configured": True}),
        patch.object(client, "soc_chat_status", return_value={"enabled": True, "document_count": 5}),
        patch.object(client, "graph_health", return_value={"status": "ok", "neo4j": True, "postgres": True}),
        patch.object(client, "inventory_status", return_value={"postgres_configured": True, "source": "postgresql"}),
    ):
        report = client.doctor()
    assert report["ok"] is True
    assert report["checks"]["backend"]["ok"] is True
    assert report["checks"]["mcp"]["saia_available"] is True
    assert report["checks"]["graph"]["ok"] is True


def test_sdk_mcp_run_query() -> None:
    data = {"tool_name": "splunk_run_query", "result": {"rows": [{"count": "7"}]}}
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.mcp_run_query("search index=main | head 5")
    assert out.tool_name == "splunk_run_query"
    call_args = m.call_args
    assert call_args[1]["json"]["tool_name"] == "splunk_run_query"
    assert "search index=main" in call_args[1]["json"]["arguments"]["search_query"]


def test_sdk_mcp_saia_ask() -> None:
    data = {"tool_name": "saia_ask_splunk_question", "result": {"answer": "main index has auth logs"}}
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.mcp_saia_ask("What indexes have auth data?", additional_context="user=jdoe")
    assert out.tool_name == "saia_ask_splunk_question"
    payload = m.call_args[1]["json"]
    assert payload["arguments"]["prompt"] == "What indexes have auth data?"
    assert payload["arguments"]["additional_context"] == "user=jdoe"


def test_sdk_run_full_investigation() -> None:
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    cls = MagicMock(model_dump=MagicMock(return_value={"track": "security"}))
    triage = MagicMock(model_dump=MagicMock(return_value={"agent_summary": "test summary"}))
    spl = MagicMock(model_dump=MagicMock(return_value={"source": "rule_based"}))
    with (
        patch.object(client, "classify_alert", return_value=cls),
        patch.object(client, "run_agent_triage", return_value=triage),
        patch.object(client, "suggest_spl", return_value=spl) as m_spl,
        patch.object(client, "mcp_status", return_value={"connected": True}),
    ):
        result = client.run_full_investigation({"normalized": {"user": "jdoe"}, "operator_goal": "investigate"})
    assert result["classification"]["track"] == "security"
    assert result["triage"]["agent_summary"] == "test summary"
    assert result["mcp_status"]["connected"] is True
    m_spl.assert_called_once()


@pytest.mark.asyncio
async def test_async_sdk_ingest_alert() -> None:
    data = {"ok": True, "sid": "1749825600.1"}
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        result = await client.ingest_alert({"sid": "1749825600.1"})
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_async_sdk_llm_status() -> None:
    data = {"litellm_model": "claude-3", "litellm_api_key_configured": False}
    client = AsyncTsocSdkClient(base_url=_BASE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        result = await client.llm_status()
    assert result["litellm_model"] == "claude-3"


@pytest.mark.asyncio
async def test_async_sdk_doctor() -> None:
    client = AsyncTsocSdkClient(base_url=_BASE)
    with (
        patch.object(client, "health", new_callable=AsyncMock, return_value={"status": "ok"}),
        patch.object(client, "mcp_status", new_callable=AsyncMock, return_value={"configured": True, "connected": True}),
        patch.object(client, "llm_status", new_callable=AsyncMock, return_value={"litellm_model": "x", "litellm_api_key_configured": True}),
        patch.object(client, "soc_chat_status", new_callable=AsyncMock, return_value={"enabled": True}),
        patch.object(client, "graph_health", new_callable=AsyncMock, return_value={"status": "ok"}),
        patch.object(client, "inventory_status", new_callable=AsyncMock, return_value={"postgres_configured": True}),
    ):
        report = await client.doctor()
    assert report["ok"] is True


@pytest.mark.asyncio
async def test_async_sdk_mcp_run_query() -> None:
    data = {"tool_name": "splunk_run_query", "result": []}
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        out = await client.mcp_run_query("search index=main")
    assert out.tool_name == "splunk_run_query"


@pytest.mark.asyncio
async def test_async_sdk_run_full_investigation() -> None:
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    cls = MagicMock(model_dump=MagicMock(return_value={"track": "observability"}))
    triage = MagicMock(model_dump=MagicMock(return_value={"agent_summary": "cpu spike"}))
    spl = MagicMock(model_dump=MagicMock(return_value={"source": "llm"}))
    with (
        patch.object(client, "classify_alert", new_callable=AsyncMock, return_value=cls),
        patch.object(client, "run_agent_triage", new_callable=AsyncMock, return_value=triage),
        patch.object(client, "suggest_spl", new_callable=AsyncMock, return_value=spl),
        patch.object(client, "mcp_status", new_callable=AsyncMock, return_value={"connected": False}),
    ):
        result = await client.run_full_investigation({"normalized": {"cpu": 95}})
    assert result["classification"]["track"] == "observability"


def test_evaluate_score_connectivity_perfect() -> None:
    from devtools.evaluate import _score_connectivity
    from devtools.workflows import build_doctor_report

    doctor = build_doctor_report(
        health={"status": "ok"},
        mcp_status={"configured": True, "connected": True, "saia_available": True},
        llm_status={"litellm_model": "gpt-4", "litellm_api_key_configured": True},
        soc_chat_status={"enabled": True, "document_count": 1},
        graph_health={"status": "ok"},
        inventory_status={"postgres_configured": True},
    )
    score, details = _score_connectivity(doctor)
    assert score == 100
    assert details["saia_available"] is True
    assert details["graph_ok"] is True


def test_evaluate_score_mcp_spl_perfect() -> None:
    from devtools.evaluate import _score_mcp_spl

    score, details = _score_mcp_spl({
        "source": "splunk_mcp_saia",
        "spl": "search index=main user=jdoe | stats count",
        "explanation": "failed logins",
    })
    assert score == 100
    assert details["source_ok"] is True


# ---------------------------------------------------------------------------
# Extended SDK API coverage (inventory, graph, chat sessions, gap, integrations)
# ---------------------------------------------------------------------------


def test_sdk_gap_suggest() -> None:
    data = {
        "should_suggest_question": True,
        "gap_summary": "Unknown contractor access",
        "question_for_admin": "Is jdoe authorized on web-prod-01?",
    }
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.gap_suggest({"normalized": {"user": "jdoe"}})
    assert out.should_suggest_question is True


def test_sdk_inventory_status_and_users() -> None:
    user = {
        "user_id": "jdoe",
        "display_name": "John Doe",
        "risk_score": 3,
    }
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.side_effect = [
            _ok_response({"source": "postgresql", "postgres_configured": True}),
            _ok_response([user]),
        ]
        status = client.inventory_status()
        users = client.list_inventory_users()
    assert status["postgres_configured"] is True
    assert users[0].user_id == "jdoe"


def test_sdk_enrich_inventory() -> None:
    data = {
        "resolved_user_id": "jdoe",
        "resolved_asset_id": "srv-web-01",
        "confidence": "high",
        "notes": "matched hostname",
        "matched_relationship_ids": [],
    }
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.post") as m:
        m.return_value = _ok_response(data)
        out = client.enrich_inventory({"normalized": {"host": "web-prod-01", "user": "jdoe"}})
    assert out.confidence == "high"


def test_sdk_list_integrations() -> None:
    row = {
        "id": "litellm_model",
        "category": "litellm",
        "key": "LITELLM_MODEL",
        "value": "gpt-4",
        "is_secret": False,
        "builtin": True,
        "configured": True,
    }
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.return_value = _ok_response([row])
        out = client.list_integrations()
    assert out[0].id == "litellm_model"


def test_sdk_graph_findings_and_health() -> None:
    client = TsocSdkClient(base_url=_BASE)
    with patch("httpx.Client.get") as m:
        m.side_effect = [
            _ok_response({"status": "ok", "neo4j": True, "postgres": True}),
            _ok_response({"items": [], "total": 0, "limit": 20, "offset": 0}),
        ]
        health = client.graph_health()
        findings = client.graph_findings(limit=20)
    assert health["status"] == "ok"
    assert findings["total"] == 0


def test_sdk_soc_chat_conversations() -> None:
    summary = {
        "id": "conv-1",
        "title": "Investigation",
        "created_at": "2026-06-13T00:00:00",
        "updated_at": "2026-06-13T00:00:00",
        "message_count": 0,
    }
    client = TsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.Client.get") as m:
        m.return_value = _ok_response([summary])
        out = client.list_soc_chat_conversations()
    assert out[0].id == "conv-1"


def test_sdk_delete_inventory_user() -> None:
    client = TsocSdkClient(base_url=_BASE)
    resp = MagicMock()
    resp.status_code = 204
    resp.raise_for_status.return_value = None
    with patch("httpx.Client.delete") as m:
        m.return_value = resp
        client.delete_inventory_user("jdoe")
    m.assert_called_once()


@pytest.mark.asyncio
async def test_async_sdk_gap_suggest() -> None:
    data = {"should_suggest_question": False, "gap_summary": "", "question_for_admin": ""}
    client = AsyncTsocSdkClient(base_url=_BASE, max_retries=0)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m:
        m.return_value = _ok_response(data)
        out = await client.gap_suggest({"normalized": {}})
    assert out.should_suggest_question is False


@pytest.mark.asyncio
async def test_async_sdk_graph_health() -> None:
    client = AsyncTsocSdkClient(base_url=_BASE)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m:
        m.return_value = _ok_response({"status": "ok"})
        out = await client.graph_health()
    assert out["status"] == "ok"


# ---------------------------------------------------------------------------
# New CLI command tests
# ---------------------------------------------------------------------------


def test_cli_ingest_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "ingest", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"sid": "1.2", "normalized": {}}),
        patch.object(TsocSdkClient, "ingest_alert", return_value={"ok": True, "sid": "1.2"}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"ok": true' in captured.out


def test_cli_doctor_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "doctor"]),
        patch.object(TsocSdkClient, "doctor", return_value={"ok": True, "ready_for_demo": True}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"ready_for_demo": true' in captured.out


def test_cli_llm_status_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "llm-status"]),
        patch.object(TsocSdkClient, "llm_status", return_value={"litellm_model": "gpt-4"}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"litellm_model": "gpt-4"' in captured.out


def test_cli_run_analysis_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "run-analysis", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"normalized": {"user": "jdoe"}}),
        patch.object(TsocSdkClient, "run_analysis") as m,
    ):
        m.return_value = MagicMock(model_dump=MagicMock(return_value={"judge": {"verdict": "true_positive"}}))
        main()
    captured = capsys.readouterr()
    assert '"verdict": "true_positive"' in captured.out


def test_cli_search_events_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "search-events", "--limit", "5"]),
        patch.object(TsocSdkClient, "search_events", return_value={"count": 2, "results": []}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"count": 2' in captured.out


def test_cli_get_event_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "get-event", "--record-id", "99"]),
        patch.object(TsocSdkClient, "get_event", return_value={"id": 99}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"id": 99' in captured.out


def test_cli_analyst_actions_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "analyst-actions", "--record-id", "10"]),
        patch.object(TsocSdkClient, "analyst_actions", return_value={"count": 1}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"count": 1' in captured.out


def test_cli_mcp_query_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "mcp-query", "--spl", "search index=main"]),
        patch.object(TsocSdkClient, "mcp_run_query") as m,
    ):
        m.return_value = MagicMock(model_dump=MagicMock(return_value={"tool_name": "splunk_run_query", "result": []}))
        main()
    captured = capsys.readouterr()
    assert '"tool_name": "splunk_run_query"' in captured.out


def test_cli_investigate_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "investigate", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"normalized": {"user": "jdoe"}}),
        patch.object(TsocSdkClient, "run_full_investigation", return_value={"classification": {"track": "security"}}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"track": "security"' in captured.out


def test_cli_gap_suggest_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "--retries", "0", "gap-suggest", "--body", "/dev/null"]),
        patch("devtools.cli._load_json", return_value={"normalized": {"user": "jdoe"}}),
        patch.object(TsocSdkClient, "gap_suggest") as m,
    ):
        m.return_value = MagicMock(
            model_dump=MagicMock(return_value={"should_suggest_question": True, "question_for_admin": "ask admin"})
        )
        main()
    captured = capsys.readouterr()
    assert '"should_suggest_question": true' in captured.out


def test_cli_inventory_status_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "inventory-status"]),
        patch.object(TsocSdkClient, "inventory_status", return_value={"postgres_configured": True}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"postgres_configured": true' in captured.out


def test_cli_graph_health_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "graph-health"]),
        patch.object(TsocSdkClient, "graph_health", return_value={"status": "ok", "neo4j": True}),
    ):
        main()
    captured = capsys.readouterr()
    assert '"status": "ok"' in captured.out


def test_cli_chat_conversations_prints_json(capsys) -> None:
    from devtools.cli import main

    with (
        patch("sys.argv", ["cli.py", "chat-conversations"]),
        patch.object(TsocSdkClient, "list_soc_chat_conversations", return_value=[]),
    ):
        main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "[]"
