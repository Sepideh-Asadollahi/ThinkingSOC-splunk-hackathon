from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse

from api.app_errors import AppError, map_exception
from api.deps import check_ingest_bearer
from api.http_rid import http_rid
from config import Settings, get_settings
from services.correlation_integration import upsert_webhook_alert_to_graph
from models.handoff import SplunkAlertIngest, normalize_splunk_ingest_payload
from services.alert.alert_pipeline import enrich_alert_from_splunk
from services.alert.ingest_background import run_post_ingest
from services.soc_rag.index_writer import schedule_alert_index
from services.splunk_json_store import persist_splunk_ingest_summary

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/alerts/splunk-ingest",
    dependencies=[Depends(check_ingest_bearer)],
    response_model=None,
)
async def splunk_ingest(
    request: Request,
    body: Dict[str, Any],
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
):
    handoff = normalize_splunk_ingest_payload(body)
    t0 = time.perf_counter()
    do_analyze = bool(settings.tsoc_ingest_auto_analyze)

    logger.info(
        "api POST /alerts/splunk-ingest rid=%s sid=%s search_name=%s auto_analyze=%s async=%s",
        http_rid(request),
        handoff.sid,
        handoff.search_name,
        do_analyze,
        do_analyze,
    )
    try:
        enriched = await enrich_alert_from_splunk(handoff, settings)
    except AppError:
        raise
    except ValueError as e:
        logger.warning("api POST /alerts/splunk-ingest rid=%s 400: %s", http_rid(request), e)
        raise AppError.bad_request(str(e)) from e
    except Exception as e:
        logger.warning(
            "api POST /alerts/splunk-ingest rid=%s 502: %s",
            http_rid(request),
            e,
            exc_info=True,
        )
        raise map_exception(e, context="splunk ingest") from e

    try:
        await upsert_webhook_alert_to_graph(body)
    except Exception as exc:
        logger.debug("ingest graph upsert skipped rid=%s: %s", http_rid(request), exc)

    if do_analyze:
        job_id = str(uuid.uuid4())
        background_tasks.add_task(run_post_ingest, settings, handoff, enriched, auto_analyze=True)
        logger.info(
            "api POST /alerts/splunk-ingest rid=%s accepted sid=%s job_id=%s duration_ms=%.1f",
            http_rid(request),
            handoff.sid,
            job_id,
            (time.perf_counter() - t0) * 1000.0,
        )
        return JSONResponse(
            status_code=202,
            content={
                "ok": True,
                "status": "accepted",
                "job_id": job_id,
                "sid": handoff.sid,
                "search_name": handoff.search_name,
                "splunk_results_row_count": enriched.get("splunk_results_row_count"),
                "auto_analyze": True,
            },
        )

    await persist_splunk_ingest_summary(
        settings,
        handoff,
        splunk_results_row_count=int(enriched.get("splunk_results_row_count") or 0),
        splunk_results=list(enriched.get("splunk_results") or []),
    )
    schedule_alert_index(
        settings,
        handoff,
        splunk_results=list(enriched.get("splunk_results") or []),
    )

    nrows = enriched.get("splunk_results_row_count")
    logger.info(
        "api POST /alerts/splunk-ingest rid=%s done sid=%s rest_rows=%s duration_ms=%.1f",
        http_rid(request),
        handoff.sid,
        nrows,
        (time.perf_counter() - t0) * 1000.0,
    )
    return {
        "ok": True,
        "sid": handoff.sid,
        "search_name": handoff.search_name,
        "splunk_results_row_count": nrows,
        "auto_analyze": False,
    }


@router.post("/alerts/splunk-ingest-debug", dependencies=[Depends(check_ingest_bearer)])
async def splunk_ingest_debug(
    request: Request,
    body: Dict[str, Any],
    settings: Settings = Depends(get_settings),
) -> dict:
    """Same as splunk-ingest but returns full enriched payload (large). Lab use only."""
    handoff = normalize_splunk_ingest_payload(body)
    t0 = time.perf_counter()
    logger.info(
        "api POST /alerts/splunk-ingest-debug rid=%s sid=%s search_name=%s",
        http_rid(request),
        handoff.sid,
        handoff.search_name,
    )
    try:
        enriched = await enrich_alert_from_splunk(handoff, settings)
    except AppError:
        raise
    except ValueError as e:
        logger.warning("api POST /alerts/splunk-ingest-debug rid=%s 400: %s", http_rid(request), e)
        raise AppError.bad_request(str(e)) from e
    except Exception as e:
        logger.warning(
            "api POST /alerts/splunk-ingest-debug rid=%s 502: %s",
            http_rid(request),
            e,
            exc_info=True,
        )
        raise map_exception(e, context="splunk ingest debug") from e

    await persist_splunk_ingest_summary(
        settings,
        handoff,
        splunk_results_row_count=int(enriched.get("splunk_results_row_count") or 0),
        splunk_results=list(enriched.get("splunk_results") or []),
    )
    logger.info(
        "api POST /alerts/splunk-ingest-debug rid=%s done sid=%s duration_ms=%.1f",
        http_rid(request),
        handoff.sid,
        (time.perf_counter() - t0) * 1000.0,
    )
    return enriched
