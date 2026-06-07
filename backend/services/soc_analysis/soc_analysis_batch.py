"""Per-row SOC analysis for all Splunk results of one ``sid`` (batch handoff)."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from config import Settings
from models.analysis import (
    AnalysisBatchBySidRequest,
    AnalysisBatchBySidResponse,
    AnalysisRunRequest,
    RowAnalysisOutcome,
)
from models.handoff import SplunkAlertIngest
from services.alert.alert_pipeline import enrich_alert_from_splunk
from services.soc_analysis import append_analysis_log, run_analysis
from services.soc_analysis.analysis_audit import format_row_sid
from services.splunk_json_store import persist_analysis_batch_summary_to_splunk

logger = logging.getLogger(__name__)


def merge_normalized_for_row(base: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow merge: Splunk result row fields override ``base``; skip Splunk ``__mv_*`` multivalue keys."""
    out = dict(base)
    for k, v in row.items():
        sk = str(k)
        if sk.startswith("__mv_"):
            continue
        out[sk] = v
    return out


async def run_analysis_batch_by_sid(
    settings: Settings,
    body: AnalysisBatchBySidRequest,
    *,
    users: List[Dict[str, Any]],
    assets: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
) -> AnalysisBatchBySidResponse:
    """
    Splunk REST → all result rows → ``run_analysis`` per row (merged ``normalized`` + ``splunk_results`` = that row).
    """
    sid = str(body.sid).strip()
    if not sid:
        raise ValueError("sid is required")

    handoff = SplunkAlertIngest(
        sid=sid,
        search_name=body.search_name,
        normalized=body.normalized,
    )
    enriched = await enrich_alert_from_splunk(handoff, settings)
    splunk_results: List[Dict[str, Any]] = list(enriched.get("splunk_results") or [])
    total = len(splunk_results)
    cap = min(body.max_rows, total)
    slice_rows = splunk_results[:cap]

    logger.info(
        "soc_batch start sid=%s search_name=%s rest_rows=%d max_rows=%d cap=%d stop_on_error=%s",
        sid,
        body.search_name,
        total,
        body.max_rows,
        cap,
        body.stop_on_first_error,
    )
    t_batch = time.perf_counter()

    rows_out: List[RowAnalysisOutcome] = []
    base_norm = body.normalized or {}

    for i, row in enumerate(slice_rows):
        t_row = time.perf_counter()
        try:
            merged = merge_normalized_for_row(base_norm, row)
            storage_sid = format_row_sid(sid, i, total)
            req = AnalysisRunRequest(
                normalized=merged,
                search_name=body.search_name,
                sid=storage_sid,
                splunk_results=[row],
            )
            result = await run_analysis(
                settings,
                req,
                users=users,
                assets=assets,
                relationships=relationships,
                analysis_row_index=i,
            )
            append_analysis_log(settings, result)
            rows_out.append(RowAnalysisOutcome(row_index=i, ok=True, result=result))
            logger.debug(
                "soc_batch row ok sid=%s row_index=%d verdict=%s duration_ms=%.1f",
                sid,
                i,
                result.judge.verdict,
                (time.perf_counter() - t_row) * 1000.0,
            )
        except Exception as e:
            logger.warning(
                "SOC batch row %d failed for sid=%s after_ms=%.1f: %s",
                i,
                sid,
                (time.perf_counter() - t_row) * 1000.0,
                e,
                exc_info=True,
            )
            if body.stop_on_first_error:
                raise
            rows_out.append(RowAnalysisOutcome(row_index=i, ok=False, error=str(e)))

    out = AnalysisBatchBySidResponse(
        sid=sid,
        search_name=body.search_name,
        splunk_results_row_count=total,
        analyzed_row_count=len(rows_out),
        rows=rows_out,
    )
    ok_n = sum(1 for r in rows_out if r.ok)
    fail_n = sum(1 for r in rows_out if not r.ok)
    logger.info(
        "soc_batch done sid=%s analyzed=%d ok=%d fail=%d duration_ms=%.1f",
        sid,
        len(rows_out),
        ok_n,
        fail_n,
        (time.perf_counter() - t_batch) * 1000.0,
    )
    await persist_analysis_batch_summary_to_splunk(
        settings,
        sid,
        body.search_name,
        out,
        ok_count=ok_n,
        fail_count=fail_n,
    )
    return out
