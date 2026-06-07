from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from api.http_rid import http_rid
from api.deps import check_ingest_bearer
from config import Settings, get_settings
from models.observability import (
    ObservabilityAnalysisResult,
    ObservabilityBatchBySidRequest,
    ObservabilityBatchBySidResponse,
    ObservabilityRunRequest,
)
from services.soc_analysis.analysis_complete_log import log_analysis_complete
from services.observability_analysis import run_observability_analysis
from services.observability_analysis.observability_analysis_batch import run_observability_batch_by_sid
from services.inventory.inventory_loader import IncompleteOfflineInventoryError, load_inventory_tables

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/observability/run",
    dependencies=[Depends(check_ingest_bearer)],
    response_model=ObservabilityAnalysisResult,
)
async def run_observability_analysis_endpoint(
    request: Request,
    body: ObservabilityRunRequest,
    settings: Settings = Depends(get_settings),
) -> ObservabilityAnalysisResult:
    t0 = time.perf_counter()
    offline = body.users is not None and body.assets is not None and body.relationships is not None
    logger.info(
        "api POST /observability/run rid=%s sid=%s search_name=%s offline_inventory=%s splunk_result_rows=%d",
        http_rid(request),
        body.sid,
        body.search_name,
        offline,
        len(body.splunk_results or ()),
    )
    try:
        users, assets, relationships = await load_inventory_tables(
            settings, body.users, body.assets, body.relationships
        )
    except IncompleteOfflineInventoryError as e:
        logger.warning("api POST /observability/run rid=%s inventory 400: %s", http_rid(request), e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        logger.warning("api POST /observability/run rid=%s inventory 503: %s", http_rid(request), e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.warning(
            "api POST /observability/run rid=%s inventory 502: %s",
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=502,
            detail="Inventory load failed (check app name, transforms, and permissions): {0}".format(e),
        ) from e

    result = await run_observability_analysis(settings, body, users=users, assets=assets, relationships=relationships)
    duration_ms = (time.perf_counter() - t0) * 1000.0
    logger.info(
        "api POST /observability/run rid=%s done sid=%s verdict=%s duration_ms=%.1f",
        http_rid(request),
        body.sid,
        result.ops_judge.verdict,
        duration_ms,
    )
    log_analysis_complete(
        pipeline="api/observability/run",
        sid=body.sid,
        verdict=result.ops_judge.verdict,
        priority=result.ops_judge.priority,
        duration_ms=duration_ms,
    )
    return result


@router.post(
    "/observability/run-by-sid",
    dependencies=[Depends(check_ingest_bearer)],
    response_model=ObservabilityBatchBySidResponse,
)
async def run_observability_batch_by_sid_endpoint(
    request: Request,
    body: ObservabilityBatchBySidRequest,
    settings: Settings = Depends(get_settings),
) -> ObservabilityBatchBySidResponse:
    t0 = time.perf_counter()
    offline = body.users is not None and body.assets is not None and body.relationships is not None
    logger.info(
        "api POST /observability/run-by-sid rid=%s sid=%s search_name=%s max_rows=%s stop_on_first_error=%s offline_inventory=%s",
        http_rid(request),
        body.sid,
        body.search_name,
        body.max_rows,
        body.stop_on_first_error,
        offline,
    )
    try:
        users, assets, relationships = await load_inventory_tables(
            settings, body.users, body.assets, body.relationships
        )
    except IncompleteOfflineInventoryError as e:
        logger.warning("api POST /observability/run-by-sid rid=%s inventory 400: %s", http_rid(request), e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        logger.warning("api POST /observability/run-by-sid rid=%s inventory 503: %s", http_rid(request), e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.warning(
            "api POST /observability/run-by-sid rid=%s inventory 502: %s",
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=502,
            detail="Inventory load failed (check app name, transforms, and permissions): {0}".format(e),
        ) from e

    try:
        out = await run_observability_batch_by_sid(settings, body, users=users, assets=assets, relationships=relationships)
    except ValueError as e:
        logger.warning("api POST /observability/run-by-sid rid=%s batch 400: %s", http_rid(request), e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.warning(
            "api POST /observability/run-by-sid rid=%s batch 502: %s",
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail="Splunk REST or batch observability failed: {0}".format(e)) from e
    duration_ms = (time.perf_counter() - t0) * 1000.0
    logger.info(
        "api POST /observability/run-by-sid rid=%s done sid=%s analyzed=%d duration_ms=%.1f",
        http_rid(request),
        body.sid,
        out.analyzed_row_count,
        duration_ms,
    )
    log_analysis_complete(
        pipeline="api/observability/run-by-sid",
        sid=body.sid,
        duration_ms=duration_ms,
        extra="analyzed={0}".format(out.analyzed_row_count),
    )
    return out
