"""Dashboard overview API."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from api.http_rid import http_rid
from config import Settings, get_settings
from models.dashboard import DashboardOverview
from services.platform.dashboard_overview import build_dashboard_overview
from services.splunk_json_store import splunk_store_configured

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard/overview", response_model=DashboardOverview)
async def dashboard_overview(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> DashboardOverview:
    """Aggregated platform status for the analyst dashboard."""
    t0 = time.perf_counter()
    logger.info("api GET /dashboard/overview rid=%s", http_rid(request))
    if not splunk_store_configured(settings):
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
        )
    try:
        overview = await build_dashboard_overview(settings)
    except Exception as e:
        logger.warning(
            "api GET /dashboard/overview rid=%s 502: %s",
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to build dashboard overview: {0}".format(e),
        ) from e
    logger.info(
        "api GET /dashboard/overview rid=%s done duration_ms=%.1f",
        http_rid(request),
        (time.perf_counter() - t0) * 1000.0,
    )
    return overview
