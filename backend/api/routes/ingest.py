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
from services.alert.ingest_accumulator import accumulate_ingest_row
from services.alert.ingest_background import run_buffered_job_triage, run_post_ingest
from services.alert.ingest_row_shape import detect_splunk_result_row_shape, log_splunk_result_row_shape
from services.alert.ingest_request_trace import (
    build_rest_row_match_debug,
    log_ingest_delivery_summary,
    log_ingest_http_trace,
    record_ingest_http_trace,
    resolve_ingest_row_index,
)
from services.alert.ingest_webhook_payload import log_ingest_webhook_payload
from services.soc_analysis.analysis_audit import format_row_sid, splunk_job_sid
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
    trace_id = http_rid(request) or str(uuid.uuid4())
    client_host = request.client.host if request.client else "-"
    content_length = request.headers.get("content-length", "-")
    user_agent = request.headers.get("user-agent", "-")
    handoff = normalize_splunk_ingest_payload(body)
    logger.info(
        "ingest_http_request_received trace_id=%s method=POST path=/alerts/splunk-ingest "
        "client=%s content_length=%s user_agent=%s",
        trace_id,
        client_host,
        content_length,
        user_agent,
    )
    ingest_trace = record_ingest_http_trace(
        trace_id=trace_id,
        client_host=client_host,
        raw_body=body,
        handoff=handoff,
    )
    log_ingest_http_trace(ingest_trace, log=logger)
    log_ingest_webhook_payload(
        stage="webhook_received",
        raw_body=body,
        handoff=handoff,
        log=logger,
        log_full_raw_body=bool(getattr(settings, "tsoc_ingest_log_raw_webhook_body", True)),
    )
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

    # Per-row webhook buffer: Splunk sends one POST per result row. Collect every POST
    # for this sid, then analyze the whole job once (row count = buffered rows). This is
    # content-driven and does not depend on a single POST or on Splunk REST.
    if do_analyze and bool(getattr(settings, "tsoc_ingest_row_buffer", True)):
        try:
            await upsert_webhook_alert_to_graph(body)
        except Exception as exc:
            logger.debug("ingest graph upsert skipped rid=%s: %s", http_rid(request), exc)
        buffer_info = await accumulate_ingest_row(
            settings,
            handoff,
            debounce_seconds=float(getattr(settings, "tsoc_ingest_row_buffer_seconds", 3.0) or 3.0),
            flush_callback=run_buffered_job_triage,
        )
        logger.info(
            "api POST /alerts/splunk-ingest rid=%s buffered sid=%s base_sid=%s buffered_rows=%d "
            "added=%d duplicates=%d duration_ms=%.1f",
            http_rid(request),
            handoff.sid,
            buffer_info["base_sid"],
            buffer_info["buffered_rows"],
            buffer_info["added"],
            buffer_info["duplicates"],
            (time.perf_counter() - t0) * 1000.0,
        )
        return JSONResponse(
            status_code=202,
            content={
                "ok": True,
                "status": "buffered",
                "sid": handoff.sid,
                "base_sid": buffer_info["base_sid"],
                "search_name": handoff.search_name,
                "buffered_rows": buffer_info["buffered_rows"],
                "added_rows": buffer_info["added"],
                "duplicate_rows": buffer_info["duplicates"],
                "buffer_window_seconds": float(
                    getattr(settings, "tsoc_ingest_row_buffer_seconds", 3.0) or 3.0
                ),
                "ingest_http_trace": ingest_trace,
                "auto_analyze": True,
            },
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

    row_count = int(enriched.get("splunk_results_row_count") or 0)
    enriched["_ingest_http_trace"] = ingest_trace
    webhook_rows = [r for r in handoff.results if isinstance(r, dict)]
    rest_rows = list(enriched.get("splunk_results") or [])
    this_request_analyze = 1
    planned_this_request: list[str] = []
    match_debug: dict | None = None
    triage_mode = "batch"
    if len(webhook_rows) == 1:
        base_sid = splunk_job_sid(handoff.sid) or handoff.sid
        match_debug = build_rest_row_match_debug(webhook_rows[0], rest_rows)
        seq = int(ingest_trace.get("request_seq_for_sid") or 0) or None
        idx, resolved_method = resolve_ingest_row_index(webhook_rows[0], rest_rows, request_seq=seq)
        match_debug["match_method"] = resolved_method
        match_debug["matched_rest_index"] = idx
        job_n = max(len(rest_rows), idx + 1, 1)
        planned_this_request = [format_row_sid(base_sid, idx, job_n)]
        this_request_analyze = 1
        triage_mode = "per_http_request_row"
        row_shape = detect_splunk_result_row_shape(
            sid=planned_this_request[0],
            total_rows=1,
            max_rows=1,
        )
        logger.info(
            "ingest_triage_plan trace_id=%s triage_mode=per_http_request_row "
            "webhook_rows_in_body=1 rest_job_rows=%d matched_rest_index=%d "
            "row_match_method=%s planned_storage_sid=%s delivery_hint=%s",
            trace_id,
            len(rest_rows),
            idx,
            match_debug.get("match_method"),
            planned_this_request[0],
            ingest_trace.get("delivery_hint"),
        )
    else:
        row_shape = detect_splunk_result_row_shape(
            sid=handoff.sid,
            total_rows=row_count,
            max_rows=int(getattr(settings, "tsoc_ingest_auto_analyze_max_rows", 50) or 50),
        )
        this_request_analyze = int(row_shape.get("rows_to_analyze") or 0)
        planned_this_request = list(row_shape.get("planned_storage_sids") or [])
        triage_mode = "batch"
        logger.info(
            "ingest_triage_plan trace_id=%s triage_mode=batch webhook_rows_in_body=%d "
            "rest_job_rows=%d rows_to_analyze=%d planned_storage_sids=%s",
            trace_id,
            len(webhook_rows),
            len(rest_rows),
            this_request_analyze,
            planned_this_request,
        )
    log_ingest_delivery_summary(
        ingest_trace,
        match_debug=match_debug,
        planned_storage_sid=planned_this_request[0] if planned_this_request else None,
        triage_mode=triage_mode,
        log=logger,
    )
    log_ingest_webhook_payload(
        stage="after_enrich",
        raw_body=body,
        handoff=handoff,
        log=logger,
        enrichment_source=str(enriched.get("enrichment_source") or ""),
        rest_row_count=row_count,
    )
    log_splunk_result_row_shape(
        stage="after_enrich",
        search_name=handoff.search_name,
        shape=row_shape,
        log=logger,
    )

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
                "splunk_results_row_count": row_count,
                "multi_row": row_shape["multi_row"],
                "rows_to_analyze": this_request_analyze,
                "planned_storage_sids": planned_this_request,
                "splunk_job_row_count": row_count,
                "ingest_http_trace": ingest_trace,
                "triage_mode": triage_mode,
                "rest_row_match": match_debug,
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
