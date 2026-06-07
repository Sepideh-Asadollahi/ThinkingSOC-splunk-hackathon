"""Admin organizational GAP — suggest one question for an administrator (hackathon)."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, Request

from api.http_rid import http_rid

from api.deps import check_ingest_bearer
from config import Settings, get_settings
from models.admin_org import AdminOrgGapSuggestRequest, AdminOrgGapSuggestResponse
from services.soc_analysis.admin_org_gap import suggest_admin_org_gap
from services.splunk_json_store import persist_admin_org_gap_to_splunk

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/admin-org/gap-suggest",
    dependencies=[Depends(check_ingest_bearer)],
    response_model=AdminOrgGapSuggestResponse,
)
async def admin_org_gap_suggest(
    request: Request,
    body: AdminOrgGapSuggestRequest,
    settings: Settings = Depends(get_settings),
) -> AdminOrgGapSuggestResponse:
    """
    Given alert fields (and optional SOC analysis excerpts), propose whether an **organizational**
    knowledge gap exists and **one question** to ask an admin — similar in spirit to ThinkingSOC
    ``admin_org_gap`` but **without** DB, queue, or RAG.

    Uses LiteLLM when configured; otherwise a small rule-based fallback.

    When PostgreSQL store is configured, persists ``tsoc_record_type=admin_org_gap_suggest``.
    """
    t0 = time.perf_counter()
    logger.info(
        "api POST /admin-org/gap-suggest rid=%s sid=%s search_name=%s",
        http_rid(request),
        body.sid,
        body.search_name,
    )
    out = await suggest_admin_org_gap(settings, body)
    await persist_admin_org_gap_to_splunk(settings, body, out)
    logger.info(
        "api POST /admin-org/gap-suggest rid=%s done should_suggest_question=%s duration_ms=%.1f",
        http_rid(request),
        out.should_suggest_question,
        (time.perf_counter() - t0) * 1000.0,
    )
    return out
