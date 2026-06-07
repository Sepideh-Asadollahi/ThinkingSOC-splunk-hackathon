from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, Request

from api.http_rid import http_rid
from api.deps import check_ingest_bearer
from config import Settings, get_settings
from models.assistant import SplAssistantSuggestRequest, SplAssistantSuggestResponse
from services.splunk_integration.splunk_ai_assistant import suggest_spl_for_alert

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/assistant/spl-suggest",
    dependencies=[Depends(check_ingest_bearer)],
    response_model=SplAssistantSuggestResponse,
)
async def assistant_spl_suggest(
    request: Request,
    body: SplAssistantSuggestRequest,
    settings: Settings = Depends(get_settings),
) -> SplAssistantSuggestResponse:
    t0 = time.perf_counter()
    rc, src = await suggest_spl_for_alert(
        settings,
        normalized=body.normalized,
        search_name=body.search_name,
        sid=body.sid,
        splunk_results=body.splunk_results,
        objective=body.objective,
        enrichment=body.enrichment.model_dump(mode="json")
        if body.enrichment is not None
        else None,
    )
    logger.info(
        "api POST /assistant/spl-suggest rid=%s sid=%s source=%s spl_len=%d duration_ms=%.1f",
        http_rid(request),
        body.sid,
        src,
        len(rc.spl or ""),
        (time.perf_counter() - t0) * 1000.0,
    )
    return SplAssistantSuggestResponse(
        source=src,
        root_cause_spl=rc,
        spl_results=rc.spl_results,
    )

