"""Persist enrichment, LLM, and admin audit records."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config import Settings
from models.admin_org import AdminOrgGapSuggestRequest, AdminOrgGapSuggestResponse
from models.enrichment import EnrichmentResult

from .. import pg
from ._common import stored_at_iso


async def persist_admin_org_gap_to_splunk(
    settings: Settings,
    request: AdminOrgGapSuggestRequest,
    response: AdminOrgGapSuggestResponse,
) -> None:
    if not pg.splunk_store_configured(settings):
        return
    payload: Dict[str, Any] = {
        "tsoc_record_type": "admin_org_gap_suggest",
        "stored_at": stored_at_iso(),
        "sid": request.sid,
        "search_name": request.search_name,
        "request": request.model_dump(mode="json"),
        "response": response.model_dump(mode="json"),
    }
    await pg.submit_hec_event(settings, payload)


async def persist_enrichment_to_splunk(
    settings: Settings,
    normalized: Dict[str, Any],
    enrichment: EnrichmentResult,
) -> None:
    if not pg.splunk_store_configured(settings):
        return
    payload: Dict[str, Any] = {
        "tsoc_record_type": "enrichment_resolve",
        "stored_at": stored_at_iso(),
        "normalized": normalized,
        "enrichment": enrichment.model_dump(mode="json"),
    }
    await pg.submit_hec_event(settings, payload)


async def persist_llm_chat_audit_to_splunk(
    settings: Settings,
    *,
    model: str,
    message_roles: List[str],
    input_char_estimate: int,
    finish_reason: Optional[str],
    usage: Optional[Dict[str, Any]],
) -> None:
    if not pg.splunk_store_configured(settings):
        return
    cap = 500_000
    est = min(max(0, input_char_estimate), cap)
    payload: Dict[str, Any] = {
        "tsoc_record_type": "llm_chat_audit",
        "stored_at": stored_at_iso(),
        "model": model,
        "message_count": len(message_roles),
        "message_roles": message_roles,
        "input_char_estimate": est,
        "finish_reason": finish_reason,
        "usage": usage,
    }
    await pg.submit_hec_event(settings, payload)
