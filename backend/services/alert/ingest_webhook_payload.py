"""Log the exact Splunk webhook body shape for multi-row debugging."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from models.handoff import SplunkAlertIngest

logger = logging.getLogger(__name__)

_PREVIEW_MAX_CHARS = 2400


def serialize_webhook_raw_body(raw_body: Dict[str, Any], *, pretty: bool = False) -> str:
    """Full JSON serialization of the HTTP body Splunk POSTed (no truncation)."""
    kwargs: Dict[str, Any] = {"ensure_ascii": False, "default": str}
    if pretty:
        kwargs["indent"] = 2
        kwargs["sort_keys"] = True
    return json.dumps(raw_body, **kwargs)


def _truncate_json(value: Any, *, max_chars: int = _PREVIEW_MAX_CHARS) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)
    except (TypeError, ValueError):
        text = str(value)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def summarize_webhook_payload(raw_body: Dict[str, Any]) -> Dict[str, Any]:
    """Describe how Splunk sent the alert (``result`` vs ``results``, keys, preview)."""
    row = raw_body.get("result")
    results = raw_body.get("results")
    result_is_dict = isinstance(row, dict)
    results_is_list = isinstance(results, list)
    results_len = len(results) if results_is_list else 0

    first_array_row: Dict[str, Any] = {}
    if results_is_list and results and isinstance(results[0], dict):
        first_array_row = results[0]

    return {
        "top_level_keys": sorted(str(k) for k in raw_body.keys()),
        "has_result_object": result_is_dict,
        "result_field_keys": sorted(str(k) for k in row.keys()) if result_is_dict else [],
        "has_results_array": results_is_list,
        "results_array_len": results_len,
        "result_preview": _truncate_json(row if result_is_dict else {}),
        "results_first_row_preview": _truncate_json(first_array_row) if first_array_row else "",
        "sid_in_body": raw_body.get("sid") or raw_body.get("job_sid"),
        "search_name_in_body": raw_body.get("search_name") or raw_body.get("savedsearch_name"),
    }


def summarize_handoff_rows(handoff: SplunkAlertIngest) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = [r for r in handoff.results if isinstance(r, dict)]
    previews = [_truncate_json(r, max_chars=1200) for r in rows[:3]]
    return {
        "handoff_results_len": len(rows),
        "handoff_normalized_keys": sorted(str(k) for k in (handoff.normalized or {}).keys()),
        "handoff_row_previews": previews,
    }


def log_raw_webhook_body(
    *,
    stage: str,
    raw_body: Dict[str, Any],
    log: Optional[logging.Logger] = None,
    enabled: bool = True,
) -> None:
    """Log the complete raw JSON body from Splunk (for format review / debugging)."""
    if not enabled:
        return
    lg = log or logger
    compact = serialize_webhook_raw_body(raw_body, pretty=False)
    pretty = serialize_webhook_raw_body(raw_body, pretty=True)
    lg.info(
        "ingest_webhook_raw_json stage=%s byte_len=%d body=%s",
        stage,
        len(compact.encode("utf-8")),
        compact,
    )
    lg.info(
        "ingest_webhook_raw_pretty stage=%s\n%s",
        stage,
        pretty,
    )


def log_ingest_webhook_payload(
    *,
    stage: str,
    raw_body: Dict[str, Any],
    handoff: SplunkAlertIngest,
    log: Optional[logging.Logger] = None,
    enrichment_source: Optional[str] = None,
    rest_row_count: Optional[int] = None,
    log_full_raw_body: bool = False,
) -> None:
    """Console log: exact webhook format Splunk posted vs rows used after enrich."""
    lg = log or logger
    if log_full_raw_body:
        log_raw_webhook_body(stage=stage, raw_body=raw_body, log=lg, enabled=True)
    summary = summarize_webhook_payload(raw_body)
    handoff_summary = summarize_handoff_rows(handoff)

    lg.info(
        "ingest_webhook_payload stage=%s top_level_keys=%s has_result_object=%s "
        "result_field_keys=%s has_results_array=%s results_array_len=%s "
        "handoff_results_len=%d enrichment_source=%s rest_row_count=%s",
        stage,
        summary["top_level_keys"],
        summary["has_result_object"],
        summary["result_field_keys"],
        summary["has_results_array"],
        summary["results_array_len"],
        handoff_summary["handoff_results_len"],
        enrichment_source or "-",
        rest_row_count if rest_row_count is not None else "-",
    )
    if summary["has_result_object"]:
        lg.info(
            "ingest_webhook_payload stage=%s splunk_result_object_preview=%s",
            stage,
            summary["result_preview"],
        )
    if summary["results_array_len"]:
        lg.info(
            "ingest_webhook_payload stage=%s splunk_results_array_first_row_preview=%s",
            stage,
            summary["results_first_row_preview"],
        )
    for i, preview in enumerate(handoff_summary["handoff_row_previews"]):
        lg.info(
            "ingest_webhook_payload stage=%s handoff_row_preview index=%d body=%s",
            stage,
            i,
            preview,
        )
