"""Backfill RAG index from PostgreSQL tsoc_records and inventory."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from config import Settings
from models.handoff import SplunkAlertIngest
from services.splunk_json_store import search_stored_events

from .compact_alert import compact_alert_document
from .compact_analysis import compact_analysis_from_payload
from .compact_inventory import index_inventory_catalog
from .compact_observability import compact_observability_from_payload
from .index_correlation import index_correlation_catalog
from .index_writer import upsert_alert_document
from .pg_store import upsert_rag_document

logger = logging.getLogger(__name__)

_STORAGE_RECORD_TYPES = (
    "splunk_ingest",
    "soc_analysis",
    "observability_analysis",
)


async def backfill_from_storage(
    settings: Settings,
    *,
    limit_per_type: int = 200,
    dry_run: bool = False,
    include_inventory: bool = True,
) -> Dict[str, int]:
    counts: Dict[str, int] = {t: 0 for t in _STORAGE_RECORD_TYPES}
    counts["errors"] = 0

    for rec_type in _STORAGE_RECORD_TYPES:
        rows = await search_stored_events(settings, record_type=rec_type, limit=limit_per_type)
        for row in rows:
            pl = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            try:
                if rec_type == "splunk_ingest":
                    norm = pl.get("normalized") if isinstance(pl.get("normalized"), dict) else {}
                    handoff = SplunkAlertIngest(
                        sid=row.get("sid") or pl.get("sid"),
                        search_name=row.get("search_name") or pl.get("search_name"),
                        normalized=norm,
                    )
                    if dry_run:
                        _ = compact_alert_document(
                            sid=handoff.sid,
                            search_name=handoff.search_name,
                            normalized=handoff.normalized,
                        )
                    else:
                        await upsert_alert_document(settings, handoff)
                    counts["splunk_ingest"] += 1
                elif rec_type == "soc_analysis":
                    merged = dict(pl)
                    merged.setdefault("sid", row.get("sid"))
                    merged.setdefault("search_name", row.get("search_name"))
                    merged.setdefault("row_index", row.get("row_index"))
                    doc = compact_analysis_from_payload(merged)
                    if doc is None:
                        continue
                    if dry_run:
                        counts["soc_analysis"] += 1
                    else:
                        await upsert_rag_document(settings, doc)
                        counts["soc_analysis"] += 1
                else:
                    merged = dict(pl)
                    merged.setdefault("sid", row.get("sid"))
                    merged.setdefault("search_name", row.get("search_name"))
                    merged.setdefault("row_index", row.get("row_index"))
                    doc = compact_observability_from_payload(merged)
                    if doc is None:
                        continue
                    if dry_run:
                        counts["observability_analysis"] += 1
                    else:
                        await upsert_rag_document(settings, doc)
                        counts["observability_analysis"] += 1
            except Exception as e:
                logger.warning("backfill row failed type=%s id=%s: %s", rec_type, row.get("id"), e)
                counts["errors"] += 1

    if include_inventory and not dry_run:
        try:
            inv = await index_inventory_catalog(settings)
            for k, v in inv.items():
                counts[k] = counts.get(k, 0) + v
        except Exception as e:
            logger.warning("inventory index failed: %s", e)
            counts["errors"] += 1

    if settings.tsoc_correlation_enabled and not dry_run:
        try:
            corr = await index_correlation_catalog(settings)
            for k, v in corr.items():
                counts[k] = counts.get(k, 0) + v
        except Exception as e:
            logger.warning("correlation index failed: %s", e)
            counts["errors"] += 1

    return counts
