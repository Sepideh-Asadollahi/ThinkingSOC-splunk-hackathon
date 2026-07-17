"""SOC analyst chat over indexed alerts, analyses, and inventory."""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from typing import Any, Dict, List, Optional

from config import Settings
from services.llm.litellm_service import LiteLLMNotConfiguredError, litellm_chat_completion
from services.splunk_json_store import splunk_store_configured

from .models import SocChatCitation, SocChatFilters, SocChatMessage, SocChatRequest, SocChatResponse
from .retrieve import retrieve_rag_documents
from .sql_chat import is_statistical_question, run_soc_sql_chat
from .chat_store import (
    append_messages,
    create_conversation,
    get_or_create_conversation,
    load_conversation_messages,
    merge_request_messages,
)
from .chat_history import (
    build_conversation_context,
    index_chat_message_for_rag,
    retrieve_session_messages,
)
from .runbook_command import (
    detect_runbook_execution_intent,
    execute_runbook_chat_command,
)

logger = logging.getLogger(__name__)

# All doc types indexed for SOC chat (see backfill + index_inventory_catalog + index_correlation).
CHAT_DEFAULT_DOC_TYPES = [
    "splunk_alert",
    "soc_analysis",
    "observability_analysis",
    "inventory_user",
    "inventory_asset",
    "inventory_relationship",
    "correlation_finding",
    "correlation_alert",
    "correlation_attack_path",
    "runbook_draft",
    "runbook_approval",
    "runbook_run",
    "runbook_shadow_run",
    "runbook_response_preview",
    "runbook_response_decision",
    "runbook_autopilot",
]

_SYSTEM = """You are a SOC analyst assistant for ThinkingSOC.
Always answer in English, regardless of the language used in the question or retrieved context.
Answer using ONLY the retrieved context, which may include:
- Splunk alerts (essential fields)
- SOC security analyses (Defender/Hunter/Judge, triage, MITRE, investigation SPL)
- Observability analyses (diagnoser/responder/ops judge)
- Inventory users, assets, and user-asset relationships
- Graph correlation: attack discoveries (findings), correlated alert nodes, entity links, and CAUSED attack paths between alerts
- ThinkingSOC Forge: Runbook revisions, approval/reuse history, shadow evaluations, Safe Response Previews, and Runbook Autopilot agent/tool traces

If context is insufficient, say what is missing and suggest Splunk searches, the Correlation explorer UI (/correlation), or which page to check.
Cite sid, search_name, runbook_id, source_record_id, session_id, finding display_id, alert_row_id, user_id, or asset_id when referencing specific items.
Treat Safe Response Preview actions as advisory and non-executable. Never claim that Autopilot approved a Runbook or executed containment.
Keep these gates distinct: Runbook approval (`approve`) authorizes only guided read-only reuse, while a response-preview decision (`approve_for_manual_action`) only records that an analyst may continue through an external manual change process. Neither means containment executed.
For Autopilot questions, treat the session status and `next_recommended_action` as authoritative when explaining why it stopped.
Be concise and actionable."""


def _last_user_message(messages: List[Dict[str, str]]) -> str:
    for m in reversed(messages):
        if (m.get("role") or "").lower() == "user":
            return str(m.get("content") or "").strip()
    return ""


def _build_context_block(docs: List[tuple]) -> str:
    parts: List[str] = []
    for i, (doc, score) in enumerate(docs, 1):
        parts.append(
            "[{0}] type={1} sid={2} search={3} score={4}\n{5}".format(
                i,
                doc.doc_type,
                doc.sid or "-",
                doc.search_name or doc.essential.get("user_id") or doc.essential.get("asset_id") or "-",
                round(score, 3),
                doc.chunk_text,
            )
        )
    return "\n\n".join(parts)


def _log_citations_detail(rid: str, hits: List[tuple]) -> None:
    for i, (doc, score) in enumerate(hits, 1):
        logger.info(
            "soc_chat citation rid=%s rank=%d doc_type=%s doc_id=%s sid=%s score=%.4f summary=%r",
            rid,
            i,
            doc.doc_type,
            doc.doc_id,
            doc.sid,
            score,
            (doc.summary_line or "")[:120],
        )


async def _resolve_conversation_messages(
    settings: Settings,
    body: SocChatRequest,
    *,
    request_id: str,
) -> tuple[str, List[Dict[str, str]]]:
    """Load or create conversation; return (conversation_id, merged messages)."""
    cid = (body.conversation_id or "").strip()
    stored: List[Dict[str, Any]] = []
    if cid:
        await get_or_create_conversation(settings, cid)
        stored = await load_conversation_messages(settings, cid)
    else:
        created = await create_conversation(settings)
        cid = str(created["conversation_id"])

    merged = merge_request_messages(stored, body.messages)
    enriched: List[Dict[str, str]] = []
    seq_by_content: Dict[tuple, int] = {}
    for m in stored:
        key = (m.get("role"), m.get("content"))
        seq_by_content[key] = int(m.get("seq") or 0)
    for m in merged:
        key = (m["role"], m["content"])
        item = {"role": m["role"], "content": m["content"]}
        if key in seq_by_content:
            item["seq"] = seq_by_content[key]
        enriched.append(item)

    logger.info(
        "soc_chat conversation rid=%s conversation_id=%s stored=%d merged=%d",
        request_id,
        cid,
        len(stored),
        len(enriched),
    )
    return cid, enriched


async def _persist_turn(
    settings: Settings,
    conversation_id: str,
    *,
    user_message: str,
    assistant_message: str,
    sql_meta: Optional[Dict[str, Any]] = None,
    citations: Optional[List[SocChatCitation]] = None,
) -> None:
    assistant_meta: Dict[str, Any] = {}
    if sql_meta:
        assistant_meta["sql_meta"] = sql_meta
    if citations:
        assistant_meta["citations"] = [item.model_dump(mode="json") for item in citations]
    user_rows = await append_messages(
        settings,
        conversation_id,
        [SocChatMessage(role="user", content=user_message)],
    )
    assistant_rows = await append_messages(
        settings,
        conversation_id,
        [SocChatMessage(role="assistant", content=assistant_message)],
        metadata=assistant_meta,
    )
    rows = [*user_rows, *assistant_rows]
    for row in rows:
        await index_chat_message_for_rag(
            settings,
            conversation_id=conversation_id,
            message_id=int(row["message_id"]),
            role=str(row["role"]),
            content=str(row["content"]),
            seq=int(row["seq"]),
        )


async def run_soc_chat(
    settings: Settings,
    body: SocChatRequest,
    *,
    request_id: Optional[str] = None,
) -> SocChatResponse:
    rid = request_id or "-"
    t_total = time.perf_counter()

    if not splunk_store_configured(settings):
        raise RuntimeError("SOC chat requires TSOC_POSTGRES_DSN")

    conversation_id, raw_messages = await _resolve_conversation_messages(settings, body, request_id=rid)
    question = _last_user_message(raw_messages)
    if not question:
        raise ValueError("Last message must be a non-empty user message")

    runbook_intent = detect_runbook_execution_intent(
        question,
        prior_messages=raw_messages[:-1],
    )
    if runbook_intent.detected:
        logger.info(
            "soc_chat routing to runbook command rid=%s conversation_id=%s sid=%s reason=%s",
            rid,
            conversation_id,
            runbook_intent.sid,
            runbook_intent.reason,
        )
        command = await execute_runbook_chat_command(
            settings,
            runbook_intent,
            request_id=rid,
        )
        await _persist_turn(
            settings,
            conversation_id,
            user_message=question,
            assistant_message=command.answer,
            citations=command.citations,
        )
        return SocChatResponse(
            answer=command.answer,
            citations=command.citations,
            splunk_mcp_used=False,
            retrieval_backend="runbook_executor",
            retrieval_meta=command.metadata,
            conversation_id=conversation_id,
        )

    filters = body.filters or SocChatFilters()
    top_k = max(settings.tsoc_rag_chat_top_k, 10)
    doc_types = filters.doc_types or CHAT_DEFAULT_DOC_TYPES
    lookback = filters.lookback_days
    use_session_rag = len(raw_messages) > settings.tsoc_chat_history_direct_max
    session_hits = None
    if use_session_rag:
        session_hits = await retrieve_session_messages(
            settings,
            conversation_id=conversation_id,
            question=question,
            top_k=settings.tsoc_chat_history_rag_top_k,
            request_id=rid,
        )
        logger.info(
            "soc_chat session_rag rid=%s conversation_id=%s messages=%d hits=%d",
            rid,
            conversation_id,
            len(raw_messages),
            len(session_hits or []),
        )

    logger.info(
        "soc_chat start rid=%s conversation_id=%s messages=%d history_roles=%s question_len=%d "
        "top_k=%d doc_types=%s lookback_days=%s search_name_prefix=%s severity=%s "
        "embedding_model=%s vector_enable=%s sql_enable=%s session_rag=%s",
        rid,
        conversation_id,
        len(raw_messages),
        [m.get("role") for m in raw_messages[-6:]],
        len(question),
        top_k,
        doc_types,
        lookback,
        filters.search_name_prefix,
        filters.severity,
        settings.tsoc_embedding_model,
        settings.tsoc_vector_enable,
        settings.tsoc_chat_sql_enable,
        use_session_rag,
    )
    logger.info("soc_chat question rid=%s\n%s", rid, question)

    if settings.tsoc_chat_sql_enable:
        try:
            if await is_statistical_question(
                settings,
                question,
                messages=raw_messages,
                request_id=rid,
            ):
                logger.info("soc_chat routing to sql path rid=%s", rid)
                sql_out = await run_soc_sql_chat(
                    settings,
                    question,
                    messages=raw_messages,
                    filters=filters,
                    request_id=rid,
                )
                await _persist_turn(
                    settings,
                    conversation_id,
                    user_message=question,
                    assistant_message=sql_out.answer,
                    sql_meta=sql_out.sql_meta.model_dump() if sql_out.sql_meta else None,
                )
                sql_out.conversation_id = conversation_id
                return sql_out
        except Exception as exc:
            logger.warning(
                "soc_sql path failed rid=%s — falling back to RAG: %s",
                rid,
                exc,
            )

    t_retrieve = time.perf_counter()
    hits, backend = await retrieve_rag_documents(
        settings,
        question=question,
        top_k=top_k,
        lookback_days=lookback,
        doc_types=doc_types,
        search_name_prefix=filters.search_name_prefix,
        severity=filters.severity,
        request_id=rid,
    )
    retrieve_ms = (time.perf_counter() - t_retrieve) * 1000.0

    type_counts = Counter(doc.doc_type for doc, _ in hits)
    logger.info(
        "soc_chat retrieval done rid=%s backend=%s hits=%d retrieve_ms=%.1f "
        "by_type=%s context_chars=%d",
        rid,
        backend,
        len(hits),
        retrieve_ms,
        dict(type_counts),
        sum(len(doc.chunk_text or "") for doc, _ in hits),
    )
    if hits:
        _log_citations_detail(rid, hits)
    else:
        logger.warning(
            "soc_chat no retrieval hits rid=%s — LLM will answer with empty context "
            "(run ingest/analysis or POST /api/v1/soc/rag/backfill)",
            rid,
        )

    context = _build_context_block(hits)
    citations = [
        SocChatCitation(
            doc_id=doc.doc_id,
            sid=doc.sid,
            search_name=doc.search_name,
            summary_line=doc.summary_line,
            doc_type=doc.doc_type,
            similarity_score=round(score, 4),
        )
        for doc, score in hits
    ]

    conversation_block = build_conversation_context(
        settings,
        messages=raw_messages,
        question=question,
        session_hits=session_hits,
    )
    user_prompt = (
        "Retrieved SOC context (alerts, analyses, inventory, Runbooks, Autopilot traces):\n"
        "{0}\n\n"
        "Conversation:\n{1}\n\n"
        "Answer the latest user question."
    ).format(
        context or "(no matching context — run ingest/analysis and POST /api/v1/soc/rag/backfill)",
        conversation_block,
    )

    llm_model = settings.litellm_model
    max_tokens = min(settings.litellm_analysis_max_tokens, 2048)
    temperature = settings.litellm_chat_default_temperature or 0.3
    logger.info(
        "soc_chat llm start rid=%s model=%s temperature=%s max_tokens=%d "
        "prompt_chars=%d context_chars=%d",
        rid,
        llm_model,
        temperature,
        max_tokens,
        len(user_prompt),
        len(context),
    )
    logger.info("soc_chat llm_prompt rid=%s role=system\n%s", rid, _SYSTEM)
    logger.info("soc_chat llm_prompt rid=%s role=user\n%s", rid, user_prompt)

    t_llm = time.perf_counter()
    llm_fallback = False
    try:
        result = await litellm_chat_completion(
            settings,
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        answer = str(result.get("content") or "").strip()
        thinking = result.get("thinking")
        raw_content = result.get("raw_content")
        usage = result.get("usage")
        logger.info(
            "soc_chat llm done rid=%s llm_ms=%.1f answer_chars=%d usage=%s finish_reason=%s",
            rid,
            (time.perf_counter() - t_llm) * 1000.0,
            len(answer),
            usage,
            result.get("finish_reason"),
        )
        if thinking:
            logger.info("soc_chat llm_thinking rid=%s\n%s", rid, thinking)
        if raw_content and str(raw_content) != answer:
            logger.info("soc_chat llm_raw_content rid=%s\n%s", rid, raw_content)
        logger.info("soc_chat llm_answer rid=%s\n%s", rid, answer)
    except LiteLLMNotConfiguredError:
        llm_fallback = True
        logger.warning(
            "soc_chat llm not configured rid=%s — returning citation summary only",
            rid,
        )
        if hits:
            answer = (
                "LiteLLM is not configured. Top matches:\n"
                + "\n".join("- [{0}] {1}".format(c.doc_type, c.summary_line) for c in citations[:8])
            )
        else:
            raise

    total_ms = (time.perf_counter() - t_total) * 1000.0
    logger.info(
        "soc_chat done rid=%s backend=%s citations=%d llm_fallback=%s "
        "retrieve_ms=%.1f total_ms=%.1f answer_chars=%d",
        rid,
        backend,
        len(citations),
        llm_fallback,
        retrieve_ms,
        total_ms,
        len(answer or ""),
    )
    logger.info("soc_chat final_answer rid=%s\n%s", rid, answer)

    await _persist_turn(
        settings,
        conversation_id,
        user_message=question,
        assistant_message=answer or "",
        citations=citations,
    )

    return SocChatResponse(
        answer=answer,
        citations=citations,
        splunk_mcp_used=False,
        retrieval_backend=backend,
        retrieval_meta={
            "query_mode": "rag",
            "count": len(citations),
            "question": question[:200],
            "doc_types": doc_types,
            "session_rag": use_session_rag,
            "conversation_messages": len(raw_messages),
        },
        conversation_id=conversation_id,
    )
