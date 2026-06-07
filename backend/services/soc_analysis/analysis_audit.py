"""Audit helpers: row index, raw alert, analysis input/output for PostgreSQL store."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from models.analysis import SocAnalysisResult
from services.alert.alert_fields import build_alert_fields_for_llm

_ROW_SID_SUFFIX = re.compile(r"^(.+)-(\d+)$")


def parse_row_sid_suffix(sid: Optional[str]) -> Optional[int]:
    """Return 0-based row index when ``sid`` uses ``{base}-{n}`` storage format."""
    s = (sid or "").strip()
    if not s:
        return None
    m = _ROW_SID_SUFFIX.match(s)
    if not m:
        return None
    return int(m.group(2)) - 1


def resolve_storage_context(
    *,
    sid: Optional[str],
    splunk_results: List[Dict[str, Any]],
    row_index: Optional[int] = None,
    job_row_count: Optional[int] = None,
) -> tuple[str, int, int]:
    """
    Resolve ``(storage_sid, row_index, job_row_count)`` for persist and LLM input.

    Pre-suffixed storage sids (``…-1``, ``…-2``) are kept when ``splunk_results`` is a
    single-row slice from per-HTTP ingest or per-row triage dispatch.
    """
    sid_s = (sid or "").strip()
    base_sid = splunk_job_sid(sid_s) or sid_s
    rows = list(splunk_results or [])
    n_slice = len(rows)

    suffix_idx = parse_row_sid_suffix(sid_s)
    if suffix_idx is not None:
        storage_sid = sid_s
        ri = suffix_idx
        job_n = job_row_count if job_row_count is not None else max(n_slice, suffix_idx + 1)
        return storage_sid, ri, job_n

    ri = resolve_row_index(row_index, rows)
    if rows and ri >= n_slice:
        ri = max(0, n_slice - 1)
    job_n = job_row_count if job_row_count is not None else n_slice
    storage_sid = format_row_sid(base_sid, ri, job_n) if base_sid else sid_s
    return storage_sid or sid_s, ri, job_n


def splunk_job_sid(sid: Optional[str]) -> str:
    """Strip ``-{row}`` storage suffix so Splunk REST can load the parent job."""
    s = (sid or "").strip()
    if not s:
        return ""
    m = _ROW_SID_SUFFIX.match(s)
    if m:
        return m.group(1)
    return s


def format_row_sid(base_sid: Optional[str], row_index: int, total_rows: int) -> str:
    """Append 1-based row number when a search job has multiple result rows."""
    base = (base_sid or "").strip()
    if not base:
        return ""
    if total_rows <= 1:
        return base
    return "{0}-{1}".format(base, int(row_index) + 1)


def resolve_row_index(
    row_index: Optional[int],
    splunk_results: List[Dict[str, Any]],
) -> int:
    """Default row 0 when results exist; always a non-negative index for storage."""
    if row_index is not None and row_index >= 0:
        return int(row_index)
    return 0


def pick_result_row(
    splunk_results: List[Dict[str, Any]],
    row_index: int,
) -> Optional[Dict[str, Any]]:
    if not splunk_results:
        return None
    if row_index < 0 or row_index >= len(splunk_results):
        return splunk_results[0]
    row = splunk_results[row_index]
    return row if isinstance(row, dict) else None


def build_raw_alert(
    *,
    sid: Optional[str],
    search_name: Optional[str],
    normalized: Dict[str, Any],
    splunk_results: List[Dict[str, Any]],
    row_index: int,
    job_row_count: Optional[int] = None,
) -> Dict[str, Any]:
    """Full Splunk alert context for the analyzed row (required for audit/UI)."""
    result_row = pick_result_row(splunk_results, row_index)
    job_sid = splunk_job_sid(sid)
    total = job_row_count if job_row_count is not None else len(splunk_results)
    if sid and _ROW_SID_SUFFIX.match(sid):
        storage_sid = sid
    else:
        storage_sid = format_row_sid(job_sid or sid, row_index, total) if sid else sid
    return {
        "sid": storage_sid or sid,
        "splunk_job_sid": job_sid or sid,
        "search_name": search_name,
        "row_index": row_index,
        "splunk_results_row_count": total,
        "normalized": dict(normalized or {}),
        "result_row": dict(result_row) if isinstance(result_row, dict) else None,
    }


def build_analysis_input(
    *,
    search_name: Optional[str],
    normalized: Dict[str, Any],
    splunk_results: List[Dict[str, Any]],
    row_index: int,
) -> Dict[str, Any]:
    """Fields sent to LLM (alert_fields for the chosen row)."""
    alert_fields = build_alert_fields_for_llm(
        search_name=search_name,
        normalized=normalized,
        splunk_results_preview=splunk_results,
        row_index=row_index,
    )
    return {
        "row_index": row_index,
        "alert_fields": alert_fields,
    }


def build_analysis_output(result: SocAnalysisResult) -> Dict[str, Any]:
    """Compact analysis outcome for audit rows."""
    out: Dict[str, Any] = {
        "verdict": result.judge.verdict,
        "priority": result.judge.priority,
        "recommended_next_step": result.judge.recommended_next_step,
        "confidence": result.judge.confidence,
        "rationale": result.judge.rationale,
        "summary": result.summary,
        "resolved_asset_id": result.enrichment.resolved_asset_id,
        "resolved_user_id": result.enrichment.resolved_user_id,
    }
    if result.triage is not None:
        td = result.triage.model_dump(mode="json")
        out["triage"] = td
        out["review_verdict"] = td["review_verdict"]
        out["investigation_priority"] = td["investigation_priority"]
        out["triage_score"] = td["triage_score"]
        out["needs_human_review"] = td["needs_human_review"]
        if result.triage.report is not None:
            out["triage_report_headline"] = result.triage.report.headline
    return out
