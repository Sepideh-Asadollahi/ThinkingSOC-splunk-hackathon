"""HTTP per-row ingest tracing."""

from __future__ import annotations

import logging

from models.handoff import normalize_splunk_ingest_payload
from services.alert.ingest_request_trace import (
    build_rest_row_match_debug,
    classify_delivery_hint,
    fingerprint_result_row,
    log_ingest_delivery_summary,
    log_ingest_http_trace,
    match_webhook_row_to_rest_index,
    record_ingest_http_trace,
    resolve_ingest_row_index,
)


def test_fingerprint_differs_for_different_rows() -> None:
    a = fingerprint_result_row({"_time": "1", "ParentImage": "a.exe"})
    b = fingerprint_result_row({"_time": "2", "ParentImage": "b.exe"})
    assert a != b


def test_match_webhook_row_by_fingerprint() -> None:
    w = {"_time": "2", "User": "bob"}
    rest = [{"_time": "1", "User": "bob"}, {"_time": "2", "User": "bob"}]
    idx, method = match_webhook_row_to_rest_index(w, rest)
    assert idx == 1
    assert method == "fingerprint_exact"


def test_record_two_http_requests_same_sid() -> None:
    raw1 = {
        "sid": "scheduler__admin__search__foo_at_1",
        "search_name": "New TesT",
        "result": {"_time": "1", "ParentImage": "a.tmp"},
    }
    raw2 = {
        "sid": "scheduler__admin__search__foo_at_1",
        "search_name": "New TesT",
        "result": {"_time": "2", "ParentImage": "b.exe"},
    }
    h1 = normalize_splunk_ingest_payload(raw1)
    h2 = normalize_splunk_ingest_payload(raw2)
    t1 = record_ingest_http_trace(trace_id="req-1", client_host="127.0.0.1", raw_body=raw1, handoff=h1)
    t2 = record_ingest_http_trace(trace_id="req-2", client_host="127.0.0.1", raw_body=raw2, handoff=h2)
    assert t1["request_seq_for_sid"] == 1
    assert t2["request_seq_for_sid"] == 2
    assert t2["delivery_hint"] == "per_row_http_request_same_sid_different_result"
    assert t1["result_fingerprint"] != t2["result_fingerprint"]


def test_classify_delivery_hint() -> None:
    assert (
        classify_delivery_hint(
            request_seq=2,
            duplicate_result=False,
            has_results_array=False,
            results_array_len=0,
        )
        == "per_row_http_request_same_sid_different_result"
    )


def test_resolve_row_index_prefers_fingerprint() -> None:
    w = {"_time": "2", "User": "bob"}
    rest = [{"_time": "1", "User": "bob"}, {"_time": "2", "User": "bob"}]
    idx, method = resolve_ingest_row_index(w, rest, request_seq=1)
    assert idx == 1
    assert method == "fingerprint_exact"


def test_resolve_row_index_falls_back_to_request_sequence() -> None:
    """Webhook result serialization differs from REST → use HTTP arrival order."""
    # Webhook row shares no diff-fields/fingerprint with REST rows (different keys).
    webhook = {"raw": "row-from-webhook-serialization"}
    rest = [{"_time": "1", "ParentImage": "a.exe"}, {"_time": "2", "ParentImage": "b.exe"}]
    idx1, m1 = resolve_ingest_row_index(webhook, rest, request_seq=1)
    idx2, m2 = resolve_ingest_row_index(webhook, rest, request_seq=2)
    assert (idx1, m1) == (0, "http_request_sequence")
    assert (idx2, m2) == (1, "http_request_sequence")


def test_resolve_row_index_no_sequence_keeps_fallback_zero() -> None:
    webhook = {"raw": "x"}
    rest = [{"_time": "1", "a": 1}, {"_time": "2", "a": 2}]
    idx, method = resolve_ingest_row_index(webhook, rest, request_seq=None)
    assert idx == 0
    assert method == "fallback_index_0"


def test_build_rest_row_match_debug() -> None:
    w = {"_time": "2", "User": "bob"}
    rest = [{"_time": "1", "User": "bob"}, {"_time": "2", "User": "bob"}]
    dbg = build_rest_row_match_debug(w, rest)
    assert dbg["matched_rest_index"] == 1
    assert dbg["match_method"] == "fingerprint_exact"
    assert len(dbg["rest_comparisons"]) == 2
    assert dbg["rest_comparisons"][1]["fingerprint_match"] is True


def test_log_ingest_delivery_summary(caplog) -> None:
    caplog.set_level(logging.INFO)
    raw = {"sid": "job.1", "search_name": "demo", "result": {"_time": "1"}}
    handoff = normalize_splunk_ingest_payload(raw)
    trace = record_ingest_http_trace(trace_id="t1", client_host="127.0.0.1", raw_body=raw, handoff=handoff)
    log_ingest_delivery_summary(
        trace,
        match_debug=build_rest_row_match_debug({"_time": "1"}, [{"_time": "1"}]),
        planned_storage_sid="job.1",
        triage_mode="per_http_request_row",
    )
    assert any("ingest_delivery_summary" in r.getMessage() for r in caplog.records)


def test_log_ingest_http_trace(caplog) -> None:
    caplog.set_level(logging.INFO)
    raw = {
        "sid": "job.log_http_trace.unique",
        "search_name": "demo",
        "result": {"_time": "1", "Computer": "desk"},
    }
    handoff = normalize_splunk_ingest_payload(raw)
    trace = record_ingest_http_trace(trace_id="t1", client_host="10.0.0.1", raw_body=raw, handoff=handoff)
    log_ingest_http_trace(trace)
    assert any("ingest_http_trace" in r.getMessage() and "request_seq_for_sid=1" in r.getMessage() for r in caplog.records)
