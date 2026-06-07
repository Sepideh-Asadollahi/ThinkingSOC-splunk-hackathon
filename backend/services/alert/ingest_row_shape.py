"""Detect multi-row Splunk jobs and log planned per-row analysis shape."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from services.soc_analysis.analysis_audit import format_row_sid, splunk_job_sid

logger = logging.getLogger(__name__)


def detect_splunk_result_row_shape(
    *,
    sid: Optional[str],
    total_rows: int,
    max_rows: int = 50,
) -> Dict[str, Any]:
    """
    Classify whether a Splunk job needs single-row or per-row sequential analysis.

    Returns a dict used for API responses and structured console logs.
    """
    base_sid = splunk_job_sid(sid) or (sid or "").strip()
    total = max(0, int(total_rows))
    cap = max(1, min(500, int(max_rows)))
    rows_to_analyze = min(cap, total) if total > 0 else 0
    multi_row = total > 1

    planned: List[str] = []
    if total == 1 and base_sid:
        planned = [base_sid]
    elif total > 1 and base_sid:
        for i in range(rows_to_analyze):
            planned.append(format_row_sid(base_sid, i, total))

    if multi_row:
        analysis_mode = "per_row_sequential"
    elif total == 1:
        analysis_mode = "single_row"
    else:
        analysis_mode = "no_rows"

    return {
        "multi_row": multi_row,
        "total_rows": total,
        "rows_to_analyze": rows_to_analyze,
        "max_rows_cap": cap,
        "base_sid": base_sid or None,
        "planned_storage_sids": planned,
        "analysis_mode": analysis_mode,
    }


def log_splunk_result_row_shape(
    *,
    stage: str,
    search_name: Optional[str],
    shape: Dict[str, Any],
    log: Optional[logging.Logger] = None,
) -> None:
    """Emit a single INFO line to the backend console for operators."""
    lg = log or logger
    sn = search_name or "-"
    base = shape.get("base_sid") or "-"
    total = int(shape.get("total_rows") or 0)
    to_run = int(shape.get("rows_to_analyze") or 0)
    mode = shape.get("analysis_mode") or "unknown"
    planned = shape.get("planned_storage_sids") or []

    if shape.get("multi_row"):
        lg.info(
            "ingest_row_shape stage=%s multi_row=true search_name=%s base_sid=%s "
            "total_rows=%d rows_to_analyze=%d analysis_mode=%s planned_storage_sids=%s",
            stage,
            sn,
            base,
            total,
            to_run,
            mode,
            planned,
        )
    elif total == 1:
        lg.info(
            "ingest_row_shape stage=%s multi_row=false search_name=%s base_sid=%s "
            "total_rows=1 rows_to_analyze=1 analysis_mode=single_row storage_sid=%s "
            "(if Splunk UI shows more rows, check ingest_webhook_payload + enrichment_source=splunk_rest)",
            stage,
            sn,
            base,
            planned[0] if planned else base,
        )
    else:
        lg.info(
            "ingest_row_shape stage=%s multi_row=false search_name=%s base_sid=%s "
            "total_rows=0 analysis_mode=no_rows",
            stage,
            sn,
            base,
        )
