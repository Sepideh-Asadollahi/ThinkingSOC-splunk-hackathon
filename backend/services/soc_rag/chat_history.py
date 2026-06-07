"""Session-scoped RAG for long SOC chat conversations."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from config import Settings

from .models import RagAlertDocument
from .pg_store import search_rag_documents, upsert_rag_document
from .qdrant_store import qdrant_enabled, search_qdrant_documents

logger = logging.getLogger(__name__)

CHAT_MESSAGE_DOC_TYPE = "chat_message"


def chat_message_doc_id(conversation_id: str, message_id: int) -> str:
    return "chat:{0}:{1}".format(conversation_id, message_id)


async def index_chat_message_for_rag(
    settings: Settings,
    *,
    conversation_id: str,
    message_id: int,
    role: str,
    content: str,
    seq: int,
) -> None:
    chunk = (content or "").strip()
    if not chunk:
        return
    summary = "{0}: {1}".format(role, chunk[:120])
    doc = RagAlertDocument(
        doc_type=CHAT_MESSAGE_DOC_TYPE,
        doc_id=chat_message_doc_id(conversation_id, message_id),
        sid=conversation_id,
        search_name=str(seq),
        row_index=int(seq),
        essential={"role": role, "seq": seq},
        summary_line=summary,
        chunk_text=chunk[:8000],
        metadata={"conversation_id": conversation_id, "message_id": message_id, "role": role, "seq": seq},
    )
    await upsert_rag_document(settings, doc)


async def retrieve_session_messages(
    settings: Settings,
    *,
    conversation_id: str,
    question: str,
    top_k: int = 8,
    request_id: Optional[str] = None,
) -> List[Tuple[Dict[str, Any], float]]:
    """Return relevant prior session turns as ({role, content, seq}, score)."""
    rid = request_id or "-"
    doc_types = [CHAT_MESSAGE_DOC_TYPE]
    hits: List[Tuple[RagAlertDocument, float]] = []

    if qdrant_enabled(settings):
        try:
            hits = await search_qdrant_documents(
                settings,
                question=question,
                top_k=top_k,
                doc_types=doc_types,
                conversation_id=conversation_id,
            )
        except Exception as exc:
            logger.warning("session_rag qdrant failed rid=%s: %s", rid, exc)

    if not hits:
        hits = await search_rag_documents(
            settings,
            question=question,
            top_k=top_k,
            doc_types=doc_types,
            conversation_id=conversation_id,
        )

    out: List[Tuple[Dict[str, Any], float]] = []
    for doc, score in hits:
        meta = doc.metadata if isinstance(doc.metadata, dict) else {}
        out.append(
            (
                {
                    "role": str(meta.get("role") or doc.essential.get("role") or "user"),
                    "content": doc.chunk_text,
                    "seq": int(meta.get("seq") or doc.row_index or 0),
                },
                score,
            )
        )
    out.sort(key=lambda x: x[0].get("seq") or 0)
    return out


def build_conversation_context(
    settings: Settings,
    *,
    messages: List[Dict[str, str]],
    question: str,
    session_hits: Optional[List[Tuple[Dict[str, Any], float]]] = None,
) -> str:
    """
    Build conversation block for LLM prompt.

    Short threads: recent turns verbatim.
    Long threads: RAG-selected session turns + recent tail for continuity.
    """
    direct_max = max(int(settings.tsoc_chat_history_direct_max), 4)
    tail = max(int(settings.tsoc_chat_history_recent_tail), 2)
    rag_top_k = max(int(settings.tsoc_chat_history_rag_top_k), 4)

    if len(messages) <= direct_max:
        return json.dumps(messages[-direct_max:], ensure_ascii=False)

    recent = messages[-tail:]
    rag_block = ""
    if session_hits is None:
        rag_block = json.dumps(recent, ensure_ascii=False)
    else:
        selected = [hit[0] for hit in session_hits[:rag_top_k]]
        seen_seq = {m.get("seq") for m in selected if m.get("seq")}
        for m in recent:
            seq = m.get("seq")
            if seq is not None and seq in seen_seq:
                continue
            selected.append(m)
        selected.sort(key=lambda x: x.get("seq") or 0)
        rag_block = json.dumps(
            [{"role": m["role"], "content": m["content"]} for m in selected],
            ensure_ascii=False,
        )

    return (
        "Long conversation — retrieved relevant prior turns (session RAG) plus recent context:\n"
        + rag_block
    )
