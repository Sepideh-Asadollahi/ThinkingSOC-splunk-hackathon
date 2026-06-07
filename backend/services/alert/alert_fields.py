"""Flatten Splunk alert / result rows for LLM System Context."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _merge_result_row(
    normalized: Dict[str, Any],
    splunk_results_preview: List[Dict[str, Any]],
    *,
    row_index: int = 0,
) -> Dict[str, Any]:
    """Splunk row at ``row_index`` merged with normalized (row wins on conflict)."""
    merged: Dict[str, Any] = dict(normalized or {})
    if not splunk_results_preview:
        return merged
    idx = row_index if 0 <= row_index < len(splunk_results_preview) else 0
    row = splunk_results_preview[idx]
    if not isinstance(row, dict):
        return merged
    for key, val in row.items():
        sk = str(key)
        if sk.startswith("__mv_"):
            continue
        if val is not None:
            merged[sk] = val
    return merged


def build_alert_fields_for_llm(
    *,
    search_name: Optional[str],
    normalized: Dict[str, Any],
    splunk_results_preview: List[Dict[str, Any]],
    row_index: int = 0,
) -> Dict[str, Any]:
    """
    One flat object for LLM analysis: ``search_name`` plus each Splunk ``result`` field.

    Example output keys: search_name, _time, host, src, dest, user, severity, count, …
    """
    merged = _merge_result_row(normalized, splunk_results_preview, row_index=row_index)
    fields: Dict[str, Any] = {}

    sn = (search_name or "").strip()
    if sn:
        fields["search_name"] = sn
    fields["row_index"] = row_index

    for key in sorted(merged.keys()):
        if key == "search_name":
            continue
        val = merged[key]
        if val is None:
            continue
        if isinstance(val, str) and not val.strip():
            continue
        fields[key] = val

    return fields
