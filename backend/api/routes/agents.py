from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from api.deps import check_ingest_bearer, rate_limit_sensitive
from api.http_rid import http_rid
from config import Settings, get_settings
from models.agents import AgentTriageRequest, AgentTriageResponse
from services.alert.agent_triage import run_agent_triage
from services.inventory.inventory_loader import IncompleteOfflineInventoryError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/agents/triage",
    dependencies=[Depends(check_ingest_bearer), Depends(rate_limit_sensitive)],
    response_model=AgentTriageResponse,
)
async def agent_triage_endpoint(
    request: Request,
    body: AgentTriageRequest,
    settings: Settings = Depends(get_settings),
) -> AgentTriageResponse:
    t0 = time.perf_counter()
    offline = body.users is not None and body.assets is not None and body.relationships is not None
    logger.info(
        "api POST /agents/triage rid=%s sid=%s search_name=%s offline_inventory=%s",
        http_rid(request),
        body.sid,
        body.search_name,
        offline,
    )
    try:
        result = await run_agent_triage(settings, body)
    except IncompleteOfflineInventoryError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    logger.info(
        "api POST /agents/triage rid=%s done sid=%s pipeline=%s duration_ms=%.1f",
        http_rid(request),
        body.sid,
        result.classification.recommended_pipeline,
        (time.perf_counter() - t0) * 1000.0,
    )
    return result
