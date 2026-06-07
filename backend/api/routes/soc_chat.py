"""SOC chat API — grounded Q&A over indexed Splunk alerts and analyses."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from api.deps import check_ingest_bearer, rate_limit_sensitive
from api.http_rid import http_rid
from config import Settings, get_settings
from services.soc_rag.backfill import backfill_from_storage
from services.llm.litellm_service import LiteLLMProviderError, provider_error_http_status
from services.soc_rag.chat import run_soc_chat
from services.soc_rag.chat_store import (
    create_conversation,
    delete_conversation,
    ensure_chat_schema,
    get_conversation,
    list_conversations,
)
from services.soc_rag.models import (
    SocChatConversationDetail,
    SocChatConversationSummary,
    SocChatCreateConversationRequest,
    SocChatRequest,
    SocChatResponse,
    SocChatStoredMessage,
)
from services.soc_rag.pg_store import rag_document_stats
from services.soc_rag.embeddings import (
    effective_embedding_dim,
    list_embedding_model_options,
    resolve_embedding_model,
)
from services.soc_rag.qdrant_store import health_check as qdrant_health_check, qdrant_enabled
from services.splunk_json_store import splunk_store_configured

logger = logging.getLogger(__name__)
router = APIRouter()


def _iso(dt: Any) -> str:
    if dt is None:
        return ""
    return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)


def _conversation_summary(row: dict) -> SocChatConversationSummary:
    return SocChatConversationSummary(
        id=str(row["conversation_id"]),
        title=str(row.get("title") or "New chat"),
        created_at=_iso(row.get("created_at")),
        updated_at=_iso(row.get("updated_at")),
        message_count=int(row.get("message_count") or 0),
    )


@router.get(
    "/soc/chat/conversations",
    dependencies=[Depends(check_ingest_bearer)],
    response_model=list[SocChatConversationSummary],
)
async def soc_chat_list_conversations(
    settings: Settings = Depends(get_settings),
    limit: int = 100,
) -> list[SocChatConversationSummary]:
    if not splunk_store_configured(settings):
        raise HTTPException(status_code=503, detail="SOC chat requires TSOC_POSTGRES_DSN.")
    await ensure_chat_schema(settings)
    rows = await list_conversations(settings, limit=limit)
    return [_conversation_summary(r) for r in rows]


@router.post(
    "/soc/chat/conversations",
    dependencies=[Depends(check_ingest_bearer)],
    response_model=SocChatConversationSummary,
)
async def soc_chat_create_conversation(
    body: SocChatCreateConversationRequest,
    settings: Settings = Depends(get_settings),
) -> SocChatConversationSummary:
    if not splunk_store_configured(settings):
        raise HTTPException(status_code=503, detail="SOC chat requires TSOC_POSTGRES_DSN.")
    row = await create_conversation(settings, title=body.title)
    return _conversation_summary(row)


@router.get(
    "/soc/chat/conversations/{conversation_id}",
    dependencies=[Depends(check_ingest_bearer)],
    response_model=SocChatConversationDetail,
)
async def soc_chat_get_conversation(
    conversation_id: str,
    settings: Settings = Depends(get_settings),
) -> SocChatConversationDetail:
    if not splunk_store_configured(settings):
        raise HTTPException(status_code=503, detail="SOC chat requires TSOC_POSTGRES_DSN.")
    conv = await get_conversation(settings, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages: list[SocChatStoredMessage] = []
    for m in conv.get("messages") or []:
        meta = m.get("metadata") if isinstance(m.get("metadata"), dict) else {}
        sql_meta = meta.get("sql_meta")
        messages.append(
            SocChatStoredMessage(
                role=str(m.get("role") or ""),
                content=str(m.get("content") or ""),
                message_id=int(m["message_id"]) if m.get("message_id") is not None else None,
                seq=int(m["seq"]) if m.get("seq") is not None else None,
                sql_meta=sql_meta,
            )
        )
    return SocChatConversationDetail(
        id=str(conv["conversation_id"]),
        title=str(conv.get("title") or "New chat"),
        created_at=_iso(conv.get("created_at")),
        updated_at=_iso(conv.get("updated_at")),
        messages=messages,
    )


@router.delete(
    "/soc/chat/conversations/{conversation_id}",
    dependencies=[Depends(check_ingest_bearer)],
)
async def soc_chat_delete_conversation(
    conversation_id: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    if not splunk_store_configured(settings):
        raise HTTPException(status_code=503, detail="SOC chat requires TSOC_POSTGRES_DSN.")
    deleted = await delete_conversation(settings, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True, "conversation_id": conversation_id}


@router.get("/soc/chat/status")
async def soc_chat_status(settings: Settings = Depends(get_settings)) -> dict:
    pg_ok = splunk_store_configured(settings)
    stats = await rag_document_stats(settings) if pg_ok else {"document_count": 0}
    qd_ok = await qdrant_health_check(settings) if qdrant_enabled(settings) else False
    correlation_enabled = bool(settings.tsoc_correlation_enabled and pg_ok)
    neo4j_ok = False
    if correlation_enabled:
        try:
            from services.correlation_integration import _ensure_correlation_path

            _ensure_correlation_path()
            from graph_core.neo4j_driver import verify_connectivity as neo4j_ok_fn

            neo4j_ok = await neo4j_ok_fn(settings)
        except Exception:
            neo4j_ok = False
    return {
        "enabled": pg_ok,
        "postgres_configured": pg_ok,
        "vector_enabled": qdrant_enabled(settings),
        "qdrant_reachable": qd_ok,
        "qdrant_url": settings.qdrant_url if qdrant_enabled(settings) else None,
        "embedding_model": (
            resolve_embedding_model(settings.tsoc_embedding_model) if qdrant_enabled(settings) else None
        ),
        "embedding_model_config": settings.tsoc_embedding_model if qdrant_enabled(settings) else None,
        "embedding_dim": effective_embedding_dim(settings) if qdrant_enabled(settings) else None,
        "embedding_model_options": list_embedding_model_options() if qdrant_enabled(settings) else None,
        "document_count": stats.get("document_count", 0),
        "last_indexed_at": stats.get("last_indexed_at"),
        "default_retrieval": "qdrant" if qd_ok else ("postgres" if pg_ok else "none"),
        "correlation_enabled": correlation_enabled,
        "correlation_neo4j_reachable": neo4j_ok,
    }


@router.post(
    "/soc/chat",
    dependencies=[Depends(check_ingest_bearer), Depends(rate_limit_sensitive)],
    response_model=SocChatResponse,
)
async def soc_chat(
    request: Request,
    body: SocChatRequest,
    settings: Settings = Depends(get_settings),
) -> SocChatResponse:
    t0 = time.perf_counter()
    if not splunk_store_configured(settings):
        raise HTTPException(
            status_code=503,
            detail="SOC chat requires TSOC_POSTGRES_DSN.",
        )
    rid = http_rid(request)
    last_user = ""
    for m in reversed(body.messages):
        if (m.role or "").lower() == "user":
            last_user = (m.content or "").strip()
            break
    logger.info(
        "api POST /soc/chat rid=%s messages=%d last_user_len=%d",
        rid,
        len(body.messages),
        len(last_user),
    )
    if last_user:
        logger.info("api POST /soc/chat rid=%s last_user\n%s", rid, last_user)
    try:
        out = await run_soc_chat(settings, body, request_id=rid)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except LiteLLMProviderError as e:
        status = provider_error_http_status(e)
        logger.warning(
            "api POST /soc/chat rid=%s %s kind=%s: %s",
            rid,
            status,
            e.kind,
            e,
        )
        raise HTTPException(status_code=status, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("api POST /soc/chat rid=%s failed", rid)
        raise HTTPException(status_code=500, detail="SOC chat failed unexpectedly") from e
    logger.info(
        "api POST /soc/chat rid=%s done backend=%s citations=%d answer_chars=%d duration_ms=%.1f",
        rid,
        out.retrieval_backend,
        len(out.citations),
        len(out.answer or ""),
        (time.perf_counter() - t0) * 1000.0,
    )
    if out.answer:
        logger.info("api POST /soc/chat rid=%s answer\n%s", rid, out.answer)
    return out


@router.post(
    "/soc/rag/backfill",
    dependencies=[Depends(check_ingest_bearer)],
)
async def soc_rag_backfill(
    settings: Settings = Depends(get_settings),
    limit: int = 200,
) -> dict:
    if not splunk_store_configured(settings):
        raise HTTPException(status_code=503, detail="PostgreSQL not configured")
    counts = await backfill_from_storage(settings, limit_per_type=limit)
    return {"ok": True, "counts": counts}
