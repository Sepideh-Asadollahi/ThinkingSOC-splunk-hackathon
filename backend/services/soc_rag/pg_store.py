"""PostgreSQL-backed RAG document store (always available when Postgres is configured)."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from config import Settings
from services.splunk_json_store import pg as pg_store
from services.splunk_json_store.pg import jsonb_param, splunk_store_configured

from .models import RagAlertDocument, SimilarAlertItem

logger = logging.getLogger(__name__)

_RAG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tsoc_rag_documents (
    doc_id TEXT PRIMARY KEY,
    doc_type TEXT NOT NULL,
    sid TEXT NULL,
    search_name TEXT NULL,
    row_index INTEGER NOT NULL DEFAULT 0,
    essential JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary_line TEXT NOT NULL DEFAULT '',
    chunk_text TEXT NOT NULL DEFAULT '',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tsoc_rag_docs_sid ON tsoc_rag_documents (sid);
CREATE INDEX IF NOT EXISTS idx_tsoc_rag_docs_type_updated ON tsoc_rag_documents (doc_type, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_tsoc_rag_docs_search ON tsoc_rag_documents (search_name);
ALTER TABLE tsoc_rag_documents DROP COLUMN IF EXISTS ragflow_document_id;
"""


async def ensure_rag_schema(settings: Settings) -> None:
    if not splunk_store_configured(settings):
        return
    if pg_store._PG_POOL is None:
        from services.splunk_json_store.pg import init_store

        await init_store(settings)
    if pg_store._PG_POOL is None:
        return
    async with pg_store._PG_POOL.acquire() as conn:
        await conn.execute(_RAG_SCHEMA_SQL)


async def upsert_rag_document(settings: Settings, doc: RagAlertDocument) -> None:
    await ensure_rag_schema(settings)
    if pg_store._PG_POOL is None:
        return
    async with pg_store._PG_POOL.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tsoc_rag_documents (
                doc_id, doc_type, sid, search_name, row_index,
                essential, summary_line, chunk_text, metadata, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9::jsonb, now())
            ON CONFLICT (doc_id) DO UPDATE SET
                doc_type = EXCLUDED.doc_type,
                sid = EXCLUDED.sid,
                search_name = EXCLUDED.search_name,
                row_index = EXCLUDED.row_index,
                essential = EXCLUDED.essential,
                summary_line = EXCLUDED.summary_line,
                chunk_text = EXCLUDED.chunk_text,
                metadata = EXCLUDED.metadata,
                updated_at = now()
            """,
            doc.doc_id,
            doc.doc_type,
            doc.sid,
            doc.search_name,
            doc.row_index,
            jsonb_param(doc.essential),
            doc.summary_line,
            doc.chunk_text,
            jsonb_param(doc.metadata),
        )
    try:
        from .qdrant_store import index_document_vector

        await index_document_vector(settings, doc)
    except Exception as e:
        logger.warning("qdrant index failed doc_id=%s: %s", doc.doc_id, e)


def _tokenize_query(q: str) -> List[str]:
    return [t for t in re.split(r"\W+", q.lower()) if len(t) >= 2][:24]


def _score_row(query_tokens: List[str], chunk: str, summary: str, essential: Dict[str, Any]) -> float:
    if not query_tokens:
        return 0.1
    hay = (chunk + " " + summary + " " + json.dumps(essential, default=str)).lower()
    hits = sum(1 for t in query_tokens if t in hay)
    return hits / max(len(query_tokens), 1)


def _row_to_similar_item(row: Dict[str, Any], score: float) -> SimilarAlertItem:
    essential = row.get("essential") if isinstance(row.get("essential"), dict) else {}
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    return SimilarAlertItem(
        sid=row.get("sid"),
        search_name=row.get("search_name"),
        _time=str(essential.get("_time") or meta.get("_time") or ""),
        essential={k: str(v) for k, v in essential.items()},
        prior_verdict=str(meta.get("verdict") or essential.get("verdict") or "") or None,
        similarity_score=round(score, 4),
        doc_type=str(row.get("doc_type") or "splunk_alert"),
    )


async def search_rag_documents(
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
    conversation_id: Optional[str] = None,
) -> List[Tuple[RagAlertDocument, float]]:
    await ensure_rag_schema(settings)
    if pg_store._PG_POOL is None:
        return []

    where: List[str] = ["1=1"]
    args: List[Any] = []
    n = 1

    if lookback_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=int(lookback_days))
        where.append("updated_at >= ${0}".format(n))
        args.append(cutoff)
        n += 1
    if doc_types:
        where.append("doc_type = ANY(${0}::text[])".format(n))
        args.append(doc_types)
        n += 1
    if search_name_prefix:
        where.append("search_name ILIKE ${0}".format(n))
        args.append("{0}%".format(search_name_prefix.strip()))
        n += 1
    if severity:
        where.append("(essential->>'severity') = ANY(${0}::text[])".format(n))
        args.append(severity)
        n += 1
    if exclude_doc_id:
        where.append("doc_id <> ${0}".format(n))
        args.append(exclude_doc_id)
        n += 1
    if exclude_sid:
        where.append("(sid IS NULL OR sid <> ${0})".format(n))
        args.append(exclude_sid)
        n += 1
    if conversation_id:
        where.append("(metadata->>'conversation_id') = ${0}".format(n))
        args.append(conversation_id.strip())
        n += 1

    lim = max(top_k * 8, 40)
    args.append(lim)
    sql = (
        "SELECT doc_id, doc_type, sid, search_name, row_index, "
        "essential, summary_line, chunk_text, metadata "
        "FROM tsoc_rag_documents WHERE "
        + " AND ".join(where)
        + " ORDER BY updated_at DESC LIMIT $"
        + str(n)
    )

    async with pg_store._PG_POOL.acquire() as conn:
        rows = await conn.fetch(sql, *args)

    q_tokens = _tokenize_query(question)
    scored: List[Tuple[Dict[str, Any], float]] = []
    for r in rows:
        row = dict(r)
        if exclude_row_index is not None and row.get("sid") == exclude_sid:
            if int(row.get("row_index") or 0) == exclude_row_index:
                continue
        essential = row.get("essential")
        if isinstance(essential, str):
            essential = json.loads(essential)
        meta = row.get("metadata")
        if isinstance(meta, str):
            meta = json.loads(meta)
        row["essential"] = essential if isinstance(essential, dict) else {}
        row["metadata"] = meta if isinstance(meta, dict) else {}
        score = _score_row(q_tokens, row.get("chunk_text") or "", row.get("summary_line") or "", row["essential"])
        if question.strip():
            scored.append((row, score))
        else:
            scored.append((row, 0.5))
    scored.sort(key=lambda x: x[1], reverse=True)

    out: List[Tuple[RagAlertDocument, float]] = []
    for row, score in scored[:top_k]:
        doc = RagAlertDocument(
            doc_type=row["doc_type"],
            doc_id=row["doc_id"],
            sid=row.get("sid"),
            search_name=row.get("search_name"),
            row_index=int(row.get("row_index") or 0),
            essential=row["essential"],
            summary_line=row.get("summary_line") or "",
            chunk_text=row.get("chunk_text") or "",
            metadata=row["metadata"],
        )
        out.append((doc, score))
    return out


async def rag_document_stats(settings: Settings) -> Dict[str, Any]:
    await ensure_rag_schema(settings)
    if pg_store._PG_POOL is None:
        return {"document_count": 0}
    async with pg_store._PG_POOL.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT COUNT(*)::int AS cnt,
                   MAX(updated_at) AS last_updated
            FROM tsoc_rag_documents
            """
        )
    if not row:
        return {"document_count": 0}
    last = row["last_updated"]
    return {
        "document_count": int(row["cnt"] or 0),
        "last_indexed_at": last.isoformat() if last else None,
    }
