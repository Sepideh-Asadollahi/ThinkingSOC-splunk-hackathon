"""Read JSON records stored in PostgreSQL by backend storage layer."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.http_rid import http_rid
from api.storage_payload_log import (
    approx_json_bytes,
    investigation_questions_detail,
    storage_payload_summary,
)

from api.deps import check_ingest_bearer
from config import Settings, get_settings
from services.splunk_json_store import (
    get_stored_event_by_id,
    search_stored_events,
    splunk_store_configured,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/storage/events",
    dependencies=[Depends(check_ingest_bearer)],
)
async def list_stored_events(
    request: Request,
    settings: Settings = Depends(get_settings),
    sid: Optional[str] = Query(None, description="Filter by Splunk search job id (recommended)."),
    record_type: Optional[str] = Query(
        None,
        description="Filter by tsoc_record_type (e.g. soc_analysis, soc_analysis_audit, soc_investigation_raw_alert).",
    ),
    row_index: Optional[int] = Query(
        None,
        ge=0,
        description="Filter by Splunk result row index for this sid.",
    ),
    limit: int = Query(50, ge=1, le=500),
) -> Dict[str, Any]:
    """Search stored backend records (ingest summaries + analysis JSON) from PostgreSQL."""
    t0 = time.perf_counter()
    logger.info(
        "api GET /storage/events rid=%s sid=%s record_type=%s row_index=%s limit=%s",
        http_rid(request),
        sid or "-",
        record_type or "-",
        row_index if row_index is not None else "-",
        limit,
    )
    if not splunk_store_configured(settings):
        logger.warning("api GET /storage/events rid=%s 503 postgres_not_configured", http_rid(request))
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
        )
    try:
        rows: List[Dict[str, Any]] = await search_stored_events(
            settings,
            sid=sid,
            record_type=record_type,
            row_index=row_index,
            limit=limit,
        )
    except Exception as e:
        logger.warning(
            "api GET /storage/events rid=%s 502: %s",
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail="Splunk search failed: {0}".format(e)) from e

    logger.info(
        "api GET /storage/events rid=%s done count=%d postgres_configured=%s duration_ms=%.1f",
        http_rid(request),
        len(rows),
        splunk_store_configured(settings),
        (time.perf_counter() - t0) * 1000.0,
    )
    return {
        "postgres_configured": splunk_store_configured(settings),
        "count": len(rows),
        "results": rows,
    }


@router.get(
    "/storage/events/{record_id}",
    dependencies=[Depends(check_ingest_bearer)],
)
async def get_stored_event(
    request: Request,
    record_id: int,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Fetch one stored record by PostgreSQL id."""
    t0 = time.perf_counter()
    logger.info("api GET /storage/events/%s rid=%s", record_id, http_rid(request))
    if not splunk_store_configured(settings):
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
        )
    try:
        row = await get_stored_event_by_id(settings, record_id)
    except Exception as e:
        logger.warning(
            "api GET /storage/events/%s rid=%s 502: %s",
            record_id,
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail="Splunk search failed: {0}".format(e)) from e
    if row is None:
        logger.warning(
            "api GET /storage/events/%s rid=%s 404 not_found duration_ms=%.1f",
            record_id,
            http_rid(request),
            (time.perf_counter() - t0) * 1000.0,
        )
        raise HTTPException(status_code=404, detail="Record not found")

    payload = row.get("payload") if isinstance(row, dict) else None
    summary = storage_payload_summary(payload)
    json_bytes = approx_json_bytes(row)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    iq_detail = investigation_questions_detail(payload)
    logger.info(
        "api GET /storage/events/%s rid=%s done duration_ms=%.1f "
        "tsoc_record_type=%s sid=%s json_bytes=%s payload=%s questions=%s",
        record_id,
        http_rid(request),
        elapsed_ms,
        row.get("tsoc_record_type") if isinstance(row, dict) else "-",
        row.get("sid") if isinstance(row, dict) else "-",
        json_bytes if json_bytes is not None else "-",
        summary,
        iq_detail,
    )

    try:
        import json

        json.dumps(row, ensure_ascii=False, default=str)
    except Exception as ser_err:
        logger.error(
            "api GET /storage/events/%s rid=%s json_not_serializable: %s payload=%s",
            record_id,
            http_rid(request),
            ser_err,
            summary,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Stored record could not be serialized to JSON",
        ) from ser_err

    return row
