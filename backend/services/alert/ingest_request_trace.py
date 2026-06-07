"""Trace each Splunk → backend HTTP ingest (detect per-row delivery vs one-shot)."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from models.handoff import SplunkAlertIngest

logger = logging.getLogger(__name__)

_WINDOW_SECONDS = 300.0
_TRACE_LOCK = Lock()
# sid -> list of {ts, trace_id, fingerprint, result_fields}
_SID_REQUEST_HISTORY: Dict[str, List[Dict[str, Any]]] = {}

_RESULT_DIFF_FIELDS = (
    "_time",
    "Computer",
    "User",
    "Image",
    "ParentImage",
    "ParentCommandLine",
    "values(CommandLine)",
    "dest_ip",
)


def fingerprint_result_row(row: Any) -> str:
    if not isinstance(row, dict):
        return "no_result_dict"
    canonical = json.dumps(row, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def extract_result_row_fields(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    return {k: row.get(k) for k in _RESULT_DIFF_FIELDS if k in row}


def _prune_history(history: List[Dict[str, Any]], now: float) -> List[Dict[str, Any]]:
    return [h for h in history if (now - float(h.get("ts") or 0)) <= _WINDOW_SECONDS]


def classify_delivery_hint(
    *,
    request_seq: int,
    duplicate_result: bool,
    has_results_array: bool,
    results_array_len: int,
) -> str:
    if has_results_array and results_array_len > 1:
        return "multi_row_in_one_http_body_results_array"
    if request_seq > 1 and not duplicate_result:
        return "per_row_http_request_same_sid_different_result"
    if duplicate_result:
        return "duplicate_http_request_same_result_fingerprint"
    if request_seq == 1:
        return "first_http_request_for_sid_in_window"
    return "unknown"


def record_ingest_http_trace(
    *,
    trace_id: str,
    client_host: str,
    raw_body: Dict[str, Any],
    handoff: SplunkAlertIngest,
) -> Dict[str, Any]:
    """Record this HTTP POST and return trace metadata for logs + triage."""
    now = time.time()
    sid = (handoff.sid or "").strip()
    result_obj = raw_body.get("result")
    results_arr = raw_body.get("results")
    has_results_array = isinstance(results_arr, list)
    results_array_len = len(results_arr) if has_results_array else 0
    fp = fingerprint_result_row(result_obj)
    row_fields = extract_result_row_fields(result_obj)

    with _TRACE_LOCK:
        history = _prune_history(_SID_REQUEST_HISTORY.get(sid) or [], now)
        prev = history[-1] if history else None
        request_seq = len(history) + 1
        entry = {
            "ts": now,
            "trace_id": trace_id,
            "fingerprint": fp,
            "row_fields": row_fields,
        }
        history.append(entry)
        if sid:
            _SID_REQUEST_HISTORY[sid] = history

    delta_ms: Optional[float] = None
    if prev is not None:
        delta_ms = (now - float(prev["ts"])) * 1000.0
    duplicate_result = bool(prev and prev.get("fingerprint") == fp)
    delivery_hint = classify_delivery_hint(
        request_seq=request_seq,
        duplicate_result=duplicate_result,
        has_results_array=has_results_array,
        results_array_len=results_array_len,
    )

    return {
        "trace_id": trace_id,
        "client_host": client_host,
        "sid": sid or None,
        "search_name": handoff.search_name,
        "request_seq_for_sid": request_seq,
        "requests_in_window": request_seq,
        "delta_since_prev_ms": round(delta_ms, 1) if delta_ms is not None else None,
        "result_fingerprint": fp,
        "duplicate_result": duplicate_result,
        "delivery_hint": delivery_hint,
        "body_top_keys": sorted(str(k) for k in raw_body.keys()),
        "has_result_object": isinstance(result_obj, dict),
        "has_results_array": has_results_array,
        "results_array_len": results_array_len,
        "handoff_results_len": len([r for r in handoff.results if isinstance(r, dict)]),
        "result_row_fields": row_fields,
        "prior_trace_ids": [str(h.get("trace_id")) for h in (history[:-1] if sid else [])],
    }


def build_rest_row_match_debug(
    webhook_row: Dict[str, Any],
    rest_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Fingerprint each REST row vs this HTTP request's ``result`` for triage planning."""
    webhook_fp = fingerprint_result_row(webhook_row)
    comparisons: List[Dict[str, Any]] = []
    for i, row in enumerate(rest_rows):
        if not isinstance(row, dict):
            continue
        rest_fp = fingerprint_result_row(row)
        comparisons.append(
            {
                "rest_index": i,
                "rest_fingerprint": rest_fp,
                "fingerprint_match": rest_fp == webhook_fp,
                "rest_row_fields": extract_result_row_fields(row),
            }
        )
    idx, method = match_webhook_row_to_rest_index(webhook_row, rest_rows)
    return {
        "webhook_fingerprint": webhook_fp,
        "webhook_row_fields": extract_result_row_fields(webhook_row),
        "rest_row_count": len(rest_rows),
        "matched_rest_index": idx,
        "match_method": method,
        "rest_comparisons": comparisons,
    }


def log_ingest_delivery_summary(
    trace: Dict[str, Any],
    *,
    match_debug: Optional[Dict[str, Any]] = None,
    planned_storage_sid: Optional[str] = None,
    triage_mode: Optional[str] = None,
    log: Optional[logging.Logger] = None,
) -> None:
    """
    One human-readable line describing how Splunk delivered this alert.

    Use alongside ``ingest_http_trace`` when debugging per-row HTTP delivery.
    """
    lg = log or logger
    seq = int(trace.get("request_seq_for_sid") or 0)
    hint = str(trace.get("delivery_hint") or "unknown")
    sid = trace.get("sid")
    parts = [
        "ingest_delivery_summary",
        "trace_id={0}".format(trace.get("trace_id")),
        "sid={0}".format(sid),
        "http_request_number_for_sid={0}".format(seq),
        "delivery_hint={0}".format(hint),
    ]
    if seq == 1:
        parts.append(
            "interpretation=first_HTTP_POST_for_this_sid"
            if hint == "first_http_request_for_sid_in_window"
            else "interpretation=first_seen_in_300s_window"
        )
    elif hint == "per_row_http_request_same_sid_different_result":
        parts.append(
            "interpretation=Splunk_sent_separate_HTTP_POST_per_result_row_same_sid"
        )
        if trace.get("delta_since_prev_ms") is not None:
            parts.append("ms_since_previous_post={0}".format(trace.get("delta_since_prev_ms")))
    elif hint == "duplicate_http_request_same_result_fingerprint":
        parts.append("interpretation=duplicate_POST_same_result_data")

    if match_debug:
        parts.append("rest_job_rows={0}".format(match_debug.get("rest_row_count")))
        parts.append("matched_rest_index={0}".format(match_debug.get("matched_rest_index")))
        parts.append("row_match_method={0}".format(match_debug.get("match_method")))
    if planned_storage_sid:
        parts.append("planned_storage_sid={0}".format(planned_storage_sid))
    if triage_mode:
        parts.append("triage_mode={0}".format(triage_mode))

    lg.info(" ".join(parts))

    row_fields = trace.get("result_row_fields") or {}
    if row_fields:
        lg.info(
            "ingest_delivery_summary trace_id=%s this_http_result_row=%s",
            trace.get("trace_id"),
            json.dumps(row_fields, ensure_ascii=False, default=str),
        )

    if match_debug and match_debug.get("rest_comparisons"):
        lg.info(
            "ingest_delivery_summary trace_id=%s webhook_vs_rest_fingerprints=%s",
            trace.get("trace_id"),
            json.dumps(match_debug["rest_comparisons"], ensure_ascii=False, default=str),
        )


def log_ingest_http_trace(
    trace: Dict[str, Any],
    *,
    log: Optional[logging.Logger] = None,
) -> None:
    lg = log or logger
    lg.info(
        "ingest_http_trace trace_id=%s client=%s sid=%s search_name=%s "
        "request_seq_for_sid=%d requests_in_window=%d delta_since_prev_ms=%s "
        "result_fingerprint=%s duplicate_result=%s delivery_hint=%s "
        "body_top_keys=%s has_result_object=%s has_results_array=%s results_array_len=%d "
        "handoff_results_len=%d prior_trace_ids=%s",
        trace.get("trace_id"),
        trace.get("client_host"),
        trace.get("sid"),
        trace.get("search_name"),
        trace.get("request_seq_for_sid"),
        trace.get("requests_in_window"),
        trace.get("delta_since_prev_ms"),
        trace.get("result_fingerprint"),
        trace.get("duplicate_result"),
        trace.get("delivery_hint"),
        trace.get("body_top_keys"),
        trace.get("has_result_object"),
        trace.get("has_results_array"),
        trace.get("results_array_len"),
        trace.get("handoff_results_len"),
        trace.get("prior_trace_ids"),
    )
    row_fields = trace.get("result_row_fields") or {}
    if row_fields:
        lg.info(
            "ingest_http_trace trace_id=%s result_row_fields=%s",
            trace.get("trace_id"),
            json.dumps(row_fields, ensure_ascii=False, default=str),
        )

    prior_ids = trace.get("prior_trace_ids") or []
    if prior_ids:
        lg.info(
            "ingest_http_trace trace_id=%s note=same_sid_seen_before prior_trace_ids=%s "
            "likely_per_row_http_delivery=%s",
            trace.get("trace_id"),
            prior_ids,
            trace.get("delivery_hint") == "per_row_http_request_same_sid_different_result",
        )


def match_webhook_row_to_rest_index(
    webhook_row: Dict[str, Any],
    rest_rows: List[Dict[str, Any]],
) -> Tuple[int, str]:
    """
    Map this HTTP request's ``result`` row to an index in REST job results.

    Returns (index, match_method).
    """
    if not rest_rows:
        return 0, "no_rest_rows"
    if len(rest_rows) == 1:
        return 0, "single_rest_row"

    target_fp = fingerprint_result_row(webhook_row)
    for i, row in enumerate(rest_rows):
        if fingerprint_result_row(row) == target_fp:
            return i, "fingerprint_exact"

    for i, row in enumerate(rest_rows):
        if not isinstance(row, dict):
            continue
        score = 0
        for key in _RESULT_DIFF_FIELDS:
            if key in webhook_row and key in row and webhook_row.get(key) == row.get(key):
                score += 1
        if score >= 3:
            return i, "field_overlap_{0}".format(score)

    return 0, "fallback_index_0"


def resolve_ingest_row_index(
    webhook_row: Dict[str, Any],
    rest_rows: List[Dict[str, Any]],
    *,
    request_seq: Optional[int] = None,
) -> Tuple[int, str]:
    """Authoritative job-row index for this HTTP POST.

    Prefer a strong fingerprint/field match of the webhook ``result`` to a REST row.
    When that is ambiguous (webhook serialization differs from REST, so every POST
    would otherwise collapse to index 0), fall back to the per-sid HTTP request order:
    Splunk fires one POST per result in order, so the Nth POST maps to the Nth row.
    This guarantees distinct POSTs map to distinct rows (no duplicate ``-1`` records).
    """
    idx, method = match_webhook_row_to_rest_index(webhook_row, rest_rows)
    if method == "fingerprint_exact" or method.startswith("field_overlap"):
        return idx, method
    # Weak match (fallback_index_0) with multiple REST rows → disambiguate by arrival order.
    if request_seq and request_seq >= 1 and len(rest_rows) > 1:
        seq_idx = request_seq - 1
        if 0 <= seq_idx < len(rest_rows):
            return seq_idx, "http_request_sequence"
    return idx, method
