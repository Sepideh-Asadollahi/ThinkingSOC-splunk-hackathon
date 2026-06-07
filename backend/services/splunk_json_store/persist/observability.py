"""Persist observability pipeline results."""

from __future__ import annotations

from typing import Any, Dict, Optional

from config import Settings
from models.observability import ObservabilityAnalysisResult, ObservabilityRunRequest

from .. import pg
from ._common import stored_at_iso


async def persist_observability_analysis_to_splunk(
    settings: Settings,
    body: ObservabilityRunRequest,
    result: ObservabilityAnalysisResult,
    *,
    row_index: Optional[int] = None,
    raw_alert: Optional[Dict[str, Any]] = None,
    analysis_input: Optional[Dict[str, Any]] = None,
    analysis_output: Optional[Dict[str, Any]] = None,
) -> None:
    if not pg.splunk_store_configured(settings):
        return
    from services.soc_analysis.analysis_audit import build_analysis_input, build_raw_alert, resolve_row_index

    idx = resolve_row_index(row_index, body.splunk_results)
    raw = raw_alert or build_raw_alert(
        sid=body.sid,
        search_name=body.search_name,
        normalized=body.normalized,
        splunk_results=body.splunk_results,
        row_index=idx,
    )
    inp = analysis_input or build_analysis_input(
        search_name=body.search_name,
        normalized=body.normalized,
        splunk_results=body.splunk_results,
        row_index=idx,
    )
    triage_dump = result.triage.model_dump(mode="json") if result.triage else None
    payload: Dict[str, Any] = {
        "tsoc_record_type": "observability_analysis",
        "stored_at": stored_at_iso(),
        "sid": body.sid,
        "search_name": body.search_name,
        "row_index": idx,
        "raw_alert": raw,
        "analysis_input": inp,
        "analysis_output": analysis_output,
        "analysis": result.model_dump(mode="json"),
    }
    if triage_dump is not None:
        payload["triage"] = triage_dump
    await pg.submit_hec_event(settings, payload)
