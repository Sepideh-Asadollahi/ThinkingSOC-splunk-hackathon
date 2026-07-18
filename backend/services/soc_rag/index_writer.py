"""Index alerts and analyses into PostgreSQL + Qdrant."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from config import Settings
from models.analysis import SocAnalysisResult
from models.handoff import SplunkAlertIngest
from models.observability import ObservabilityAnalysisResult

from .compact_alert import compact_alert_document
from .compact_analysis import compact_analysis_document
from .pg_store import upsert_rag_document

logger = logging.getLogger(__name__)


async def upsert_alert_document(
    settings: Settings,
    handoff: SplunkAlertIngest,
    *,
    splunk_results: Optional[list] = None,
    track: Optional[str] = None,
) -> None:
    if not handoff.sid and not handoff.normalized:
        return
    try:
        doc = compact_alert_document(
            sid=handoff.sid,
            search_name=handoff.search_name,
            normalized=handoff.normalized,
            splunk_results=splunk_results,
            row_index=0,
            track=track,
        )
        await upsert_rag_document(settings, doc)
    except Exception as e:
        logger.warning("soc rag index alert failed sid=%s: %s", handoff.sid, e, exc_info=True)


async def upsert_analysis_document(
    settings: Settings,
    *,
    sid: Optional[str],
    search_name: Optional[str],
    normalized: dict,
    result: SocAnalysisResult,
    row_index: int = 0,
    inventory_user: Optional[dict] = None,
    inventory_asset: Optional[dict] = None,
) -> None:
    try:
        doc = compact_analysis_document(
            sid=sid,
            search_name=search_name,
            normalized=normalized,
            result=result,
            row_index=row_index,
            inventory_user=inventory_user,
            inventory_asset=inventory_asset,
        )
        await upsert_rag_document(settings, doc)
    except Exception as e:
        logger.warning("soc rag index analysis failed sid=%s: %s", sid, e, exc_info=True)


async def upsert_observability_document(
    settings: Settings,
    *,
    sid: Optional[str],
    search_name: Optional[str],
    normalized: dict,
    result: ObservabilityAnalysisResult,
    row_index: int = 0,
) -> None:
    from .compact_observability import compact_observability_from_payload

    try:
        payload = {
            "sid": sid,
            "search_name": search_name,
            "row_index": row_index,
            "normalized": normalized,
            "analysis": result.model_dump(mode="json"),
        }
        doc = compact_observability_from_payload(payload)
        if doc:
            await upsert_rag_document(settings, doc)
    except Exception as e:
        logger.warning("soc rag index observability failed sid=%s: %s", sid, e, exc_info=True)


def schedule_alert_index(
    settings: Settings,
    handoff: SplunkAlertIngest,
    *,
    splunk_results: Optional[list] = None,
) -> None:
    if not settings.tsoc_postgres_dsn:
        return

    async def _run() -> None:
        await upsert_alert_document(settings, handoff, splunk_results=splunk_results)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run())
    except RuntimeError:
        asyncio.run(_run())


async def upsert_runbook_artifact_document(
    settings: Settings,
    *,
    record_type: str,
    event: Dict[str, Any],
) -> None:
    """Best-effort ThinkingSOC Lite indexing kept outside the authoritative write path."""
    try:
        from .compact_runbook import compact_runbook_artifact

        doc = compact_runbook_artifact(record_type, event)
        if doc is not None:
            await upsert_rag_document(settings, doc)
    except Exception as exc:
        logger.warning(
            "soc rag index runbook failed record_type=%s runbook_id=%s: %s",
            record_type,
            event.get("runbook_id"),
            exc,
            exc_info=True,
        )


def schedule_runbook_artifact_index(
    settings: Settings,
    *,
    record_type: str,
    event: Dict[str, Any],
) -> None:
    if not settings.tsoc_postgres_dsn:
        return

    async def _run() -> None:
        await upsert_runbook_artifact_document(
            settings,
            record_type=record_type,
            event=event,
        )

    try:
        asyncio.get_running_loop().create_task(_run())
    except RuntimeError:
        asyncio.run(_run())
