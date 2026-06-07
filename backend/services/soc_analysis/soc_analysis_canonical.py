"""
Canonical alert / context prefix for SOC analysis.

Use a stable, `sort_keys=True` JSON blob as the shared prefix so each LLM node can append
prior outputs after the same prefix (cache-friendly, consistent shape).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from services.alert.alert_fields import build_alert_fields_for_llm


def build_canonical_static_context(
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    sid: Optional[str],
    splunk_results_preview: List[Dict[str, Any]],
    enrichment: Dict[str, Any],
    risk_context: str,
    inventory_user: Optional[Dict[str, Any]],
    inventory_asset: Optional[Dict[str, Any]],
    threat_intel: Optional[Dict[str, Any]] = None,
    similar_alert_context: Optional[Dict[str, Any]] = None,
    row_index: int = 0,
) -> str:
    """
    Single canonical JSON string (sorted keys) — the **System Context** core for every LLM node.
    """
    alert_fields = build_alert_fields_for_llm(
        search_name=search_name,
        normalized=normalized,
        splunk_results_preview=splunk_results_preview,
        row_index=row_index,
    )
    payload: Dict[str, Any] = {
        "alert_core": {
            "search_name": search_name,
            "sid": sid,
            "row_index": row_index,
            "alert_fields": alert_fields,
            "normalized": normalized,
            "splunk_results_preview": splunk_results_preview,
        },
        "enrichment": enrichment,
        "risk_context": risk_context,
        "inventory_user": inventory_user,
        "inventory_asset": inventory_asset,
    }
    if threat_intel:
        payload["threat_intel"] = threat_intel
    if similar_alert_context:
        payload["similar_alert_context"] = similar_alert_context
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
