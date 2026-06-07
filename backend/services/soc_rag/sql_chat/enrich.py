"""Post-SQL enrichment: attach computed triage fields from payload (not keyword routing)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from config import Settings
from services.splunk_json_store import get_stored_event_by_id
from services.triage.triage_priority import triage_from_stored_payload

logger = logging.getLogger(__name__)


def _payload_dict(raw: Any) -> Optional[Dict[str, Any]]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _apply_triage_to_row(item: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    merged = dict(payload)
    merged.setdefault("tsoc_record_type", item.get("tsoc_record_type"))
    triage = triage_from_stored_payload(merged)
    if triage is None:
        return False
    item.setdefault("investigation_priority", triage.investigation_priority)
    item.setdefault("triage_score", triage.triage_score)
    item.setdefault("review_verdict", triage.review_verdict)
    item.setdefault("source_track", triage.source_track)
    return True


async def enrich_rows_with_triage(
    settings: Settings,
    rows: List[Dict[str, Any]],
    *,
    tables_used: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    For tsoc_records analysis rows, add investigation_priority / triage_score
    using the same logic as GET /api/v1/triage/queue (triage_from_stored_payload).
    """
    if "tsoc_records" not in (tables_used or []):
        return rows
    if not rows:
        return rows

    out: List[Dict[str, Any]] = []
    enriched = 0
    for row in rows:
        item = dict(row)
        pl = _payload_dict(item.get("payload"))
        if pl and _apply_triage_to_row(item, pl):
            enriched += 1
        elif item.get("id") is not None:
            stored = await get_stored_event_by_id(settings, int(item["id"]))
            if stored:
                spl = _payload_dict(stored.get("payload"))
                if spl and _apply_triage_to_row(item, spl):
                    enriched += 1
        out.append(item)
    if enriched:
        logger.info(
            "soc_sql enrich_triage tables=%s rows=%d enriched=%d",
            tables_used,
            len(rows),
            enriched,
        )
    return out
