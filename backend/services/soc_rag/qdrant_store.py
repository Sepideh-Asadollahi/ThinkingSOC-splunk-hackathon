"""Qdrant vector index — lightweight semantic RAG (https://github.com/qdrant/qdrant)."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)

from config import Settings

from .embeddings import effective_embedding_dim, embed_text
from .models import RagAlertDocument

logger = logging.getLogger(__name__)

_client: Optional[AsyncQdrantClient] = None

QDRANT_FIX_HINT = (
    "if QDRANT_URL is local, an http(s)_proxy/ALL_PROXY env var may be hijacking the "
    "127.0.0.1 connection (SSL/EOF) — the client now bypasses it; otherwise reset the volume: "
    "cd backend && (docker rm -f tsoc-qdrant 2>/dev/null; "
    "docker volume rm tsoc_qdrant_data backend_tsoc_qdrant_data 2>/dev/null; "
    "docker compose up -d qdrant) — verify: curl -sf --noproxy '*' http://127.0.0.1:6333/readyz"
)


def qdrant_enabled(settings: Settings) -> bool:
    return bool(settings.tsoc_vector_enable and (settings.qdrant_url or "").strip())


def _normalize_qdrant_url(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if not u:
        return u
    if "://" not in u:
        u = "http://{0}".format(u)
    return u


def _is_local_url(url: str) -> bool:
    u = _normalize_qdrant_url(url)
    return "127.0.0.1" in u or "localhost" in u or "://[::1]" in u


def _proxy_env_present() -> bool:
    keys = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
    return any((os.environ.get(k) or "").strip() for k in keys)


def _point_id(doc_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "tsoc:{0}".format(doc_id)))


def reset_qdrant_client() -> None:
    global _client
    _client = None


def _client_for(settings: Settings) -> AsyncQdrantClient:
    global _client
    if _client is None:
        url = _normalize_qdrant_url(settings.qdrant_url)
        # trust_env=False: never route a local Qdrant connection through a system proxy.
        # On hosts where install.sh needed HTTP(S)_PROXY to pull images, the proxy would
        # otherwise hijack 127.0.0.1:6333 and surface as "SSL: UNEXPECTED_EOF_WHILE_READING".
        _client = AsyncQdrantClient(
            url=url,
            prefer_grpc=False,
            https=url.startswith("https://"),
            check_compatibility=False,
            timeout=30.0,
            trust_env=False,
        )
    return _client


async def health_check(settings: Settings) -> bool:
    if not qdrant_enabled(settings):
        return False
    try:
        # trust_env=False mirrors the qdrant client: bypass proxy for the local readiness probe.
        async with httpx.AsyncClient(timeout=5.0, trust_env=False) as http:
            r = await http.get("{0}/readyz".format(_normalize_qdrant_url(settings.qdrant_url)))
            return r.status_code == 200
    except Exception:
        return False


async def wait_for_qdrant_ready(settings: Settings, *, timeout_sec: int = 60) -> bool:
    """Wait until Qdrant HTTP /readyz succeeds (container may still be starting)."""
    if not qdrant_enabled(settings):
        return False
    if _is_local_url(settings.qdrant_url) and _proxy_env_present():
        logger.info(
            "qdrant: proxy env detected; using direct connection (trust_env=False) for %s",
            settings.qdrant_url,
        )
    deadline = asyncio.get_running_loop().time() + timeout_sec
    while asyncio.get_running_loop().time() < deadline:
        if await health_check(settings):
            return True
        await asyncio.sleep(2)
    return False


async def _collection_vector_dim(client: AsyncQdrantClient, name: str) -> Optional[int]:
    try:
        info = await client.get_collection(name)
        vectors = info.config.params.vectors
        size = getattr(vectors, "size", None)
        return int(size) if size is not None else None
    except Exception:
        return None


async def ensure_qdrant_collection(settings: Settings) -> None:
    if not qdrant_enabled(settings):
        return
    client = _client_for(settings)
    name = settings.qdrant_collection
    dim = effective_embedding_dim(settings)
    existing_dim = await _collection_vector_dim(client, name)
    if existing_dim is not None and existing_dim != dim:
        logger.warning(
            "qdrant collection %s has dim=%s but TSOC_EMBEDDING_DIM=%s; recreating (run /soc/rag/backfill)",
            name,
            existing_dim,
            dim,
        )
        await client.delete_collection(name)
        existing_dim = None
    if existing_dim is None:
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        logger.info("qdrant collection created name=%s dim=%s", name, dim)


def _payload_from_doc(doc: RagAlertDocument) -> Dict[str, Any]:
    return {
        "doc_id": doc.doc_id,
        "doc_type": doc.doc_type,
        "sid": doc.sid,
        "search_name": doc.search_name,
        "row_index": doc.row_index,
        "summary_line": doc.summary_line[:500],
        "chunk_text": (doc.chunk_text or "")[:6000],
        "essential": doc.essential,
        "metadata": doc.metadata,
        "updated_at": datetime.now(timezone.utc).timestamp(),
    }


def _doc_from_payload(payload: Dict[str, Any]) -> RagAlertDocument:
    essential = payload.get("essential")
    meta = payload.get("metadata")
    return RagAlertDocument(
        doc_id=str(payload.get("doc_id") or ""),
        doc_type=str(payload.get("doc_type") or "splunk_alert"),
        sid=payload.get("sid"),
        search_name=payload.get("search_name"),
        row_index=int(payload.get("row_index") or 0),
        essential=essential if isinstance(essential, dict) else {},
        summary_line=str(payload.get("summary_line") or ""),
        chunk_text=str(payload.get("chunk_text") or ""),
        metadata=meta if isinstance(meta, dict) else {},
    )


async def index_document_vector(settings: Settings, doc: RagAlertDocument) -> None:
    if not qdrant_enabled(settings):
        return
    await ensure_qdrant_collection(settings)
    vector = await embed_text(settings, doc.chunk_text or doc.summary_line)
    client = _client_for(settings)
    await client.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            PointStruct(
                id=_point_id(doc.doc_id),
                vector=vector,
                payload=_payload_from_doc(doc),
            )
        ],
    )


def _build_filter(
    *,
    doc_types: Optional[List[str]] = None,
    exclude_doc_id: Optional[str] = None,
    lookback_days: Optional[int] = None,
    search_name_prefix: Optional[str] = None,
    severity: Optional[List[str]] = None,
    conversation_id: Optional[str] = None,
) -> Optional[Filter]:
    must: List[FieldCondition] = []
    if doc_types:
        must.append(FieldCondition(key="doc_type", match=MatchAny(any=doc_types)))
    if lookback_days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=int(lookback_days))).timestamp()
        must.append(FieldCondition(key="updated_at", range=Range(gte=cutoff)))
    if severity:
        must.append(FieldCondition(key="essential.severity", match=MatchAny(any=severity)))
    if conversation_id:
        must.append(
            FieldCondition(
                key="metadata.conversation_id",
                match=MatchValue(value=conversation_id.strip()),
            )
        )
    must_not: List[FieldCondition] = []
    if exclude_doc_id:
        must_not.append(FieldCondition(key="doc_id", match=MatchValue(value=exclude_doc_id)))
    if not must and not must_not:
        return None
    return Filter(must=must or None, must_not=must_not or None)


async def search_qdrant_documents(
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
    if not qdrant_enabled(settings):
        return []
    await ensure_qdrant_collection(settings)
    vector = await embed_text(settings, question)
    qfilter = _build_filter(
        doc_types=doc_types,
        exclude_doc_id=exclude_doc_id,
        lookback_days=lookback_days,
        search_name_prefix=search_name_prefix,
        severity=severity,
        conversation_id=conversation_id,
    )
    client = _client_for(settings)
    response = await client.query_points(
        collection_name=settings.qdrant_collection,
        query=vector,
        limit=max(top_k * 2, top_k),
        query_filter=qfilter,
        with_payload=True,
    )
    results = response.points or []
    out: List[Tuple[RagAlertDocument, float]] = []
    for hit in results:
        payload = hit.payload or {}
        if exclude_sid and payload.get("sid") == exclude_sid:
            if exclude_row_index is not None and int(payload.get("row_index") or 0) == exclude_row_index:
                continue
        if exclude_doc_id and payload.get("doc_id") == exclude_doc_id:
            continue
        doc = _doc_from_payload(payload)
        if search_name_prefix:
            sn = (doc.search_name or "").lower()
            if not sn.startswith(search_name_prefix.strip().lower()):
                continue
        if not doc.doc_id:
            continue
        score = float(hit.score or 0.0)
        out.append((doc, score))
        if len(out) >= top_k:
            break
    return out
