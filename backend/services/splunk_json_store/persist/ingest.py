"""Persist Splunk webhook ingest summaries."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config import Settings
from models.handoff import SplunkAlertIngest

from .. import pg
from ._common import stored_at_iso


async def persist_splunk_ingest_summary(
    settings: Settings,
    handoff: SplunkAlertIngest,
    *,
    splunk_results_row_count: int,
    splunk_results: Optional[List[Dict[str, Any]]] = None,
) -> None:
    if not pg.splunk_store_configured(settings):
        return
    from services.soc_analysis.analysis_audit import build_raw_alert

    rows = list(splunk_results or [])
    raw_alert = build_raw_alert(
        sid=handoff.sid,
        search_name=handoff.search_name,
        normalized=handoff.normalized,
        splunk_results=rows,
        row_index=0,
    )
    payload: Dict[str, Any] = {
        "tsoc_record_type": "splunk_ingest",
        "stored_at": stored_at_iso(),
        "sid": handoff.sid,
        "search_name": handoff.search_name,
        "row_index": 0,
        "orig_sid": handoff.orig_sid,
        "splunk_results_row_count": splunk_results_row_count,
        "normalized": handoff.normalized,
        "raw_alert": raw_alert,
        "severity_override": handoff.severity_override,
        "include_raw": handoff.include_raw,
    }
    await pg.submit_hec_event(settings, payload)
