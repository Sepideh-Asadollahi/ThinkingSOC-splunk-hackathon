"""Investigation timeline and analyst human-in-the-loop actions."""

from __future__ import annotations

import logging
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.deps import check_ingest_bearer
from api.http_rid import http_rid
from config import Settings, get_settings
from services.investigation.investigation_workflow import (
    build_investigation_timeline,
    list_analyst_actions_for_record,
    record_analyst_action,
)
from services.splunk_json_store import splunk_store_configured

logger = logging.getLogger(__name__)
router = APIRouter()


class AnalystActionBody(BaseModel):
    action: Literal["acknowledge", "escalate"]
    note: Optional[str] = Field(None, max_length=2000)
    analyst: Optional[str] = Field(None, max_length=128)


@router.get(
    "/investigation/records/{record_id}/timeline",
    dependencies=[Depends(check_ingest_bearer)],
)
async def get_investigation_timeline(
    request: Request,
    record_id: int,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Chronological steps for the alert tied to a storage record (by sid)."""
    if not splunk_store_configured(settings):
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
        )
    try:
        data = await build_investigation_timeline(settings, record_id)
    except Exception as e:
        logger.warning(
            "api GET investigation timeline record_id=%s rid=%s err=%s",
            record_id,
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail=str(e)) from e
    if not data.get("found"):
        raise HTTPException(status_code=404, detail="Record not found")
    return data


@router.get(
    "/investigation/records/{record_id}/analyst-actions",
    dependencies=[Depends(check_ingest_bearer)],
)
async def get_investigation_analyst_actions(
    request: Request,
    record_id: int,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Latest analyst acknowledge/escalate entries for this investigation record."""
    if not splunk_store_configured(settings):
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
        )
    actions = await list_analyst_actions_for_record(settings, record_id)
    return {
        "record_id": record_id,
        "count": len(actions),
        "results": actions,
    }


@router.post(
    "/investigation/records/{record_id}/analyst-actions",
    dependencies=[Depends(check_ingest_bearer)],
)
async def post_investigation_analyst_action(
    request: Request,
    record_id: int,
    body: AnalystActionBody,
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Record analyst acknowledge or escalate (human gate; no firewall execution)."""
    if not splunk_store_configured(settings):
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL store not configured; set TSOC_POSTGRES_DSN.",
        )
    try:
        result = await record_analyst_action(
            settings,
            record_id,
            action=body.action,
            note=body.note,
            analyst=body.analyst,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Record not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.warning(
            "api POST analyst-action record_id=%s rid=%s err=%s",
            record_id,
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail=str(e)) from e

    if not result.get("ok"):
        raise HTTPException(status_code=502, detail="Failed to persist analyst action")

    logger.info(
        "api POST analyst-action record_id=%s action=%s rid=%s",
        record_id,
        body.action,
        http_rid(request),
    )
    actions = await list_analyst_actions_for_record(settings, record_id)
    return {
        "record_id": record_id,
        "saved": result,
        "latest": actions[0] if actions else None,
        "results": actions,
    }
