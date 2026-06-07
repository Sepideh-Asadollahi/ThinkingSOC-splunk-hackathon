"""Shared /predict + MCP execute pipeline."""

from __future__ import annotations

from services.investigation.spl_predict_pipeline import (
    REST_ALL_TIME_EARLIEST,
    REST_ALL_TIME_LATEST,
    SPL_ALL_TIME_WINDOW,
    classify_saia_predict_failure,
    default_investigation_time_window,
    discourage_values_aggregation,
    parse_mcp_execute_result,
    parse_time_window,
    quote_spl_colon_field_values,
    rows_from_mcp_result,
    strip_time_range_from_spl,
)
from services.investigation.spl_tstats_sanitize import sanitize_spl_draft
from config import Settings


def test_default_investigation_time_window_all_time() -> None:
    s = Settings(tsoc_investigation_spl_time_window="")
    assert default_investigation_time_window(s) == SPL_ALL_TIME_WINDOW


def test_parse_time_window_all_time() -> None:
    earliest, latest = parse_time_window(SPL_ALL_TIME_WINDOW)
    assert earliest == REST_ALL_TIME_EARLIEST
    assert latest == REST_ALL_TIME_LATEST


def test_strip_time_range_from_spl() -> None:
    raw = "index=botsv1 host=h1 earliest=-48h latest=now | stats count"
    assert "earliest" not in strip_time_range_from_spl(raw).lower()
    assert "latest" not in strip_time_range_from_spl(raw).lower()
    assert SPL_ALL_TIME_WINDOW == "earliest=1 latest=now"


def test_discourage_values_aggregation() -> None:
    raw = 'search index=main | stats values(DestinationIp) as ips, values(Port) as ports'
    out = discourage_values_aggregation(raw)
    assert "values(" not in out
    assert "dc(DestinationIp)" in out
    assert "dc(Port) as ports" in out


def test_quote_spl_colon_field_values() -> None:
    raw = (
        "search index=botsv1 sourcetype=XmlWinEventLog:Microsoft-Windows-Sysmon/Operational "
        "source=WinEventLog:Microsoft-Windows-Sysmon/Operational | head 5"
    )
    out = quote_spl_colon_field_values(raw)
    assert 'sourcetype="XmlWinEventLog:Microsoft-Windows-Sysmon/Operational"' in out
    assert 'source="WinEventLog:Microsoft-Windows-Sysmon/Operational"' in out
    sanitized = sanitize_spl_draft(
        "search index=botsv1 sourcetype=XmlWinEventLog:Microsoft-Windows-Sysmon/Operational | head 5"
    )
    assert 'sourcetype="XmlWinEventLog:Microsoft-Windows-Sysmon/Operational"' in sanitized
    deduped = sanitize_spl_draft(raw)
    assert deduped.count('source="WinEventLog:Microsoft-Windows-Sysmon/Operational"') == 1


def test_parse_mcp_execute_result_dict() -> None:
    raw = {
        "results": [{"_time": "1", "host": "h1"}],
        "total_rows": 1,
        "truncated": False,
    }
    rows, total, trunc = parse_mcp_execute_result(raw)
    assert len(rows) == 1
    assert total == 1
    assert trunc is False


def test_rows_from_mcp_nested_json_string() -> None:
    inner = '{"results":[{"host":"x"}],"total_rows":1}'
    rows = rows_from_mcp_result(inner)
    assert rows == [{"host": "x"}]


def test_classify_saia_predict_failure_metering() -> None:
    exc = RuntimeError(
        'predict request failed (HTTP 500): {"error":"Unable to check metering and throttling status"}'
    )
    category, reason, hint = classify_saia_predict_failure(exc)
    assert category == "saia_metering"
    assert "metering" in reason.lower()
    assert "LiteLLM" in hint


def test_classify_saia_predict_failure_auth() -> None:
    exc = RuntimeError("predict request failed (HTTP 401): unauthorized")
    category, reason, hint = classify_saia_predict_failure(exc)
    assert category == "saia_auth"
    assert "authentication" in reason.lower()
    assert "SPLUNK_USERNAME" in hint
