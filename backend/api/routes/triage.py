"""Triage queue API — priority-sorted analyst review list."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.deps import check_ingest_bearer
from api.http_rid import http_rid
from config import Settings, get_settings
from services.splunk_json_store import splunk_store_configured
from services.triage.triage_queue import TrackFilter, build_triage_queue_items

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/triage/queue",
    dependencies=[Depends(check_ingest_bearer)],
)
async def list_triage_queue(
    request: Request,
    settings: Settings = Depends(get_settings),
    track: TrackFilter = Query("all", description="Filter by pipeline track."),
    limit: int = Query(50, ge=1, le=500),
) -> Dict[str, Any]:
    """Return stored analyses sorted by triage_score (highest first)."""
    t0 = time.perf_counter()
    logger.info(
        "api GET /triage/queue rid=%s track=%s limit=%s",
        http_rid(request),
        track,
        limit,
    )
    if not splunk_store_configured(settings):
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
        )

    try:
        items: List[Dict[str, Any]] = await build_triage_queue_items(
            settings,
            track=track,
            limit=limit,
        )
    except Exception as e:
        logger.warning("api GET /triage/queue rid=%s 502: %s", http_rid(request), e, exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to load triage queue: {0}".format(e)) from e

    logger.info(
        "api GET /triage/queue rid=%s done count=%d duration_ms=%.1f",
        http_rid(request),
        len(items),
        (time.perf_counter() - t0) * 1000.0,
    )
    return {
        "postgres_configured": True,
        "track": track,
        "count": len(items),
        "results": items,
    }
