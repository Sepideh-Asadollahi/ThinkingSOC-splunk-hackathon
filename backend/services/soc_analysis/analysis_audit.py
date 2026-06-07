"""Audit helpers: row index, raw alert, analysis input/output for PostgreSQL store."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.analysis import SocAnalysisResult
from services.alert.alert_fields import build_alert_fields_for_llm


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
) -> Dict[str, Any]:
    """Full Splunk alert context for the analyzed row (required for audit/UI)."""
    result_row = pick_result_row(splunk_results, row_index)
    return {
        "sid": sid,
        "search_name": search_name,
        "row_index": row_index,
        "splunk_results_row_count": len(splunk_results),
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
