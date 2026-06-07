"""Unified retrieval: Qdrant (semantic) with PostgreSQL fallback."""

from __future__ import annotations

import logging
import time
from typing import List, Optional, Tuple

from config import Settings

from .models import RagAlertDocument
from .pg_store import search_rag_documents
from .qdrant_store import qdrant_enabled, search_qdrant_documents

logger = logging.getLogger(__name__)


async def retrieve_rag_documents(
    settings: Settings,
    *,
    question: str,
    top_k: int = 8,
    exclude_doc_id: Optional[str] = None,
    exclude_sid: Optional[str] = None,
    exclude_row_index: Optional[int] = None,
    lookback_days: Optional[int] = None,
    doc_types: Optional[List[str]] = None,
    search_name_prefix: Optional[str] = None,
    severity: Optional[List[str]] = None,
    request_id: Optional[str] = None,
) -> Tuple[List[Tuple[RagAlertDocument, float]], str]:
    """Return (hits, backend_name). Prefers Qdrant when enabled."""
    rid = request_id or "-"
    t0 = time.perf_counter()
    logger.info(
        "soc_chat retrieve start rid=%s top_k=%d doc_types=%s lookback_days=%s "
        "search_name_prefix=%s severity=%s question_len=%d question_preview=%r",
        rid,
        top_k,
        doc_types,
        lookback_days,
        search_name_prefix,
        severity,
        len(question),
        question[:200],
    )

    if qdrant_enabled(settings):
        logger.info(
            "soc_chat retrieve trying qdrant rid=%s url=%s collection=%s",
            rid,
            settings.qdrant_url,
            settings.qdrant_collection,
        )
        try:
            hits = await search_qdrant_documents(
                settings,
                question=question,
                top_k=top_k,
                exclude_doc_id=exclude_doc_id,
                exclude_sid=exclude_sid,
                exclude_row_index=exclude_row_index,
                lookback_days=lookback_days,
                doc_types=doc_types,
                search_name_prefix=search_name_prefix,
                severity=severity,
            )
            if hits:
                logger.info(
                    "soc_chat retrieve qdrant ok rid=%s hits=%d duration_ms=%.1f top=%s",
                    rid,
                    len(hits),
                    (time.perf_counter() - t0) * 1000.0,
                    _hits_log_line(hits, limit=5),
                )
                return hits, "qdrant"
            logger.info(
                "soc_chat retrieve qdrant empty rid=%s — falling back to postgres",
                rid,
            )
        except Exception as e:
            logger.warning(
                "soc_chat retrieve qdrant failed rid=%s fallback postgres: %s",
                rid,
                e,
                exc_info=True,
            )
    else:
        logger.info(
            "soc_chat retrieve qdrant disabled rid=%s vector_enable=%s — using postgres",
            rid,
            settings.tsoc_vector_enable,
        )

    hits = await search_rag_documents(
        settings,
        question=question,
        top_k=top_k,
        exclude_doc_id=exclude_doc_id,
        exclude_sid=exclude_sid,
        exclude_row_index=exclude_row_index,
        lookback_days=lookback_days,
        doc_types=doc_types,
        search_name_prefix=search_name_prefix,
        severity=severity,
    )
    logger.info(
        "soc_chat retrieve postgres ok rid=%s hits=%d duration_ms=%.1f top=%s",
        rid,
        len(hits),
        (time.perf_counter() - t0) * 1000.0,
        _hits_log_line(hits, limit=5),
    )
    return hits, "postgres"


def _hits_log_line(
    hits: List[Tuple[RagAlertDocument, float]], *, limit: int = 5
) -> str:
    parts: List[str] = []
    for doc, score in hits[:limit]:
        parts.append(
            "{0}:{1:.3f}".format(
                doc.doc_type,
                score,
            )
        )
    if len(hits) > limit:
        parts.append("+{0} more".format(len(hits) - limit))
    return " | ".join(parts) if parts else "(none)"
