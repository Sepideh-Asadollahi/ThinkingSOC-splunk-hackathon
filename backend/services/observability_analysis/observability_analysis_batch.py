"""Per-row Observability analysis for all Splunk results of one sid."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from config import Settings
from models.handoff import SplunkAlertIngest
from models.observability import (
    ObservabilityBatchBySidRequest,
    ObservabilityBatchBySidResponse,
    ObservabilityRunRequest,
    RowObservabilityOutcome,
)
from services.alert.alert_pipeline import enrich_alert_from_splunk
from services.observability_analysis import run_observability_analysis

logger = logging.getLogger(__name__)


def merge_normalized_for_row(base: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in row.items():
        sk = str(k)
        if sk.startswith("__mv_"):
            continue
        out[sk] = v
    return out


async def run_observability_batch_by_sid(
    settings: Settings,
    body: ObservabilityBatchBySidRequest,
    *,
    users: List[Dict[str, Any]],
    assets: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
) -> ObservabilityBatchBySidResponse:
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
    rows_out: List[RowObservabilityOutcome] = []

    base_norm = body.normalized or {}
    for i, row in enumerate(slice_rows):
        try:
            merged = merge_normalized_for_row(base_norm, row)
            req = ObservabilityRunRequest(
                normalized=merged,
                search_name=body.search_name,
                sid=sid,
                splunk_results=[row],
            )
            result = await run_observability_analysis(
                settings,
                req,
                users=users,
                assets=assets,
                relationships=relationships,
            )
            rows_out.append(RowObservabilityOutcome(row_index=i, ok=True, result=result))
        except Exception as e:
            logger.warning("observability batch row failed sid=%s row=%d err=%s", sid, i, e, exc_info=True)
            if body.stop_on_first_error:
                raise
            rows_out.append(RowObservabilityOutcome(row_index=i, ok=False, error=str(e)))

    return ObservabilityBatchBySidResponse(
        sid=sid,
        search_name=body.search_name,
        splunk_results_row_count=total,
        analyzed_row_count=len(rows_out),
        rows=rows_out,
    )
