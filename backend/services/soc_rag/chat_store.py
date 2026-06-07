"""PostgreSQL persistence for SOC chat conversations and messages."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import Settings
from services.splunk_json_store import pg as pg_store
from services.splunk_json_store.pg import jsonb_param, splunk_store_configured

from .models import SocChatMessage

logger = logging.getLogger(__name__)

_CHAT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tsoc_chat_conversations (
    conversation_id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'New chat',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tsoc_chat_conv_updated
    ON tsoc_chat_conversations (updated_at DESC);

CREATE TABLE IF NOT EXISTS tsoc_chat_messages (
    message_id BIGSERIAL PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES tsoc_chat_conversations(conversation_id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    seq INTEGER NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (conversation_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_tsoc_chat_msg_conv_seq
    ON tsoc_chat_messages (conversation_id, seq);
"""


def _title_from_text(text: str, *, max_len: int = 60) -> str:
    line = " ".join((text or "").strip().split())
    if not line:
        return "New chat"
    if len(line) <= max_len:
        return line
    return line[: max_len - 1].rstrip() + "…"


async def ensure_chat_schema(settings: Settings) -> None:
    if not splunk_store_configured(settings):
        return
    if pg_store._PG_POOL is None:
        from services.splunk_json_store.pg import init_store

        await init_store(settings)
    if pg_store._PG_POOL is None:
        return
    async with pg_store._PG_POOL.acquire() as conn:
        await conn.execute(_CHAT_SCHEMA_SQL)


async def list_conversations(
    settings: Settings,
    *,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    await ensure_chat_schema(settings)
    if pg_store._PG_POOL is None:
        return []
    lim = max(1, min(int(limit), 500))
    async with pg_store._PG_POOL.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.conversation_id,
                   c.title,
                   c.created_at,
                   c.updated_at,
                   COUNT(m.message_id)::int AS message_count
            FROM tsoc_chat_conversations c
            LEFT JOIN tsoc_chat_messages m USING (conversation_id)
            GROUP BY c.conversation_id, c.title, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC
            LIMIT $1
            """,
            lim,
        )
    return [dict(r) for r in rows]


async def create_conversation(
    settings: Settings,
    *,
    title: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    await ensure_chat_schema(settings)
    if pg_store._PG_POOL is None:
        raise RuntimeError("PostgreSQL store not initialized")
    cid = (conversation_id or str(uuid.uuid4())).strip()
    t = (title or "New chat").strip() or "New chat"
    async with pg_store._PG_POOL.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tsoc_chat_conversations (conversation_id, title)
            VALUES ($1, $2)
            ON CONFLICT (conversation_id) DO NOTHING
            """,
            cid,
            t,
        )
        row = await conn.fetchrow(
            """
            SELECT conversation_id, title, created_at, updated_at,
                   (SELECT COUNT(*)::int FROM tsoc_chat_messages m
                    WHERE m.conversation_id = c.conversation_id) AS message_count
            FROM tsoc_chat_conversations c
            WHERE conversation_id = $1
            """,
            cid,
        )
    out = dict(row or {"conversation_id": cid, "title": t})
    out.setdefault("message_count", 0)
    return out


async def get_or_create_conversation(
    settings: Settings,
    conversation_id: str,
    *,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Return existing conversation row or create it if missing."""
    cid = (conversation_id or "").strip()
    if not cid:
        return await create_conversation(settings, title=title)
    existing = await get_conversation(settings, cid)
    if existing is not None:
        return {
            "conversation_id": existing["conversation_id"],
            "title": existing.get("title") or "New chat",
            "created_at": existing.get("created_at"),
            "updated_at": existing.get("updated_at"),
            "message_count": int(existing.get("message_count") or 0),
        }
    return await create_conversation(settings, conversation_id=cid, title=title)


async def get_conversation(
    settings: Settings,
    conversation_id: str,
) -> Optional[Dict[str, Any]]:
    await ensure_chat_schema(settings)
    if pg_store._PG_POOL is None:
        return None
    cid = (conversation_id or "").strip()
    if not cid:
        return None
    async with pg_store._PG_POOL.acquire() as conn:
        conv = await conn.fetchrow(
            """
            SELECT conversation_id, title, created_at, updated_at
            FROM tsoc_chat_conversations
            WHERE conversation_id = $1
            """,
            cid,
        )
        if not conv:
            return None
        msg_rows = await conn.fetch(
            """
            SELECT message_id, role, content, seq, metadata, created_at
            FROM tsoc_chat_messages
            WHERE conversation_id = $1
            ORDER BY seq ASC
            """,
            cid,
        )
    messages = []
    for r in msg_rows:
        meta = r["metadata"]
        if isinstance(meta, str):
            import json

            meta = json.loads(meta)
        messages.append(
            {
                "message_id": int(r["message_id"]),
                "role": r["role"],
                "content": r["content"],
                "seq": int(r["seq"]),
                "metadata": meta if isinstance(meta, dict) else {},
                "created_at": r["created_at"],
            }
        )
    out = dict(conv)
    out["messages"] = messages
    out["message_count"] = len(messages)
    return out


async def delete_conversation(settings: Settings, conversation_id: str) -> bool:
    await ensure_chat_schema(settings)
    if pg_store._PG_POOL is None:
        return False
    cid = (conversation_id or "").strip()
    if not cid:
        return False
    async with pg_store._PG_POOL.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                DELETE FROM tsoc_rag_documents
                WHERE doc_type = 'chat_message'
                  AND (
                    sid = $1
                    OR metadata->>'conversation_id' = $1
                  )
                """,
                cid,
            )
            result = await conn.execute(
                "DELETE FROM tsoc_chat_conversations WHERE conversation_id = $1",
                cid,
            )
    return result.endswith("1")


async def load_conversation_messages(
    settings: Settings,
    conversation_id: str,
) -> List[Dict[str, Any]]:
    conv = await get_conversation(settings, conversation_id)
    if not conv:
        return []
    return [
        {"role": m["role"], "content": m["content"], "message_id": m["message_id"], "seq": m["seq"]}
        for m in conv.get("messages") or []
    ]


async def append_messages(
    settings: Settings,
    conversation_id: str,
    messages: List[SocChatMessage],
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Append chat turns and return inserted rows with message_id + seq."""
    await ensure_chat_schema(settings)
    if pg_store._PG_POOL is None:
        raise RuntimeError("PostgreSQL store not initialized")
    cid = (conversation_id or "").strip()
    if not cid or not messages:
        return []

    meta = metadata or {}
    inserted: List[Dict[str, Any]] = []
    async with pg_store._PG_POOL.acquire() as conn:
        async with conn.transaction():
            exists = await conn.fetchval(
                "SELECT 1 FROM tsoc_chat_conversations WHERE conversation_id = $1",
                cid,
            )
            if not exists:
                raise ValueError("Conversation not found")

            next_seq = await conn.fetchval(
                "SELECT COALESCE(MAX(seq), 0) FROM tsoc_chat_messages WHERE conversation_id = $1",
                cid,
            )
            next_seq = int(next_seq or 0)

            first_user: Optional[str] = None
            for msg in messages:
                role = (msg.role or "").strip().lower()
                content = (msg.content or "").strip()
                if not role or not content:
                    continue
                next_seq += 1
                if role == "user" and first_user is None:
                    first_user = content
                row = await conn.fetchrow(
                    """
                    INSERT INTO tsoc_chat_messages (conversation_id, role, content, seq, metadata)
                    VALUES ($1, $2, $3, $4, $5::jsonb)
                    RETURNING message_id, role, content, seq, created_at
                    """,
                    cid,
                    role,
                    content,
                    next_seq,
                    jsonb_param(meta),
                )
                inserted.append(dict(row))

            title_update = ""
            if first_user:
                current_title = await conn.fetchval(
                    "SELECT title FROM tsoc_chat_conversations WHERE conversation_id = $1",
                    cid,
                )
                if (current_title or "").strip() in ("", "New chat"):
                    title_update = _title_from_text(first_user)

            if title_update:
                await conn.execute(
                    """
                    UPDATE tsoc_chat_conversations
                    SET title = $2, updated_at = now()
                    WHERE conversation_id = $1
                    """,
                    cid,
                    title_update,
                )
            else:
                await conn.execute(
                    """
                    UPDATE tsoc_chat_conversations
                    SET updated_at = now()
                    WHERE conversation_id = $1
                    """,
                    cid,
                )
    return inserted


def merge_request_messages(
    stored: List[Dict[str, Any]],
    request_messages: List[SocChatMessage],
) -> List[Dict[str, str]]:
    """Combine DB history with client payload; append only new tail if client resends history."""
    base = [{"role": m["role"], "content": m["content"]} for m in stored]
    incoming = [{"role": (m.role or "").lower(), "content": (m.content or "").strip()} for m in request_messages]
    incoming = [m for m in incoming if m["role"] and m["content"]]

    if not incoming:
        return base
    if not base:
        return incoming

    if len(incoming) >= len(base):
        prefix_ok = True
        for i, b in enumerate(base):
            if i >= len(incoming):
                prefix_ok = False
                break
            inc = incoming[i]
            if inc["role"] != b["role"] or inc["content"] != b["content"]:
                prefix_ok = False
                break
        if prefix_ok:
            return incoming

    last = incoming[-1]
    if last["role"] == "user":
        if base and base[-1]["role"] == "user" and base[-1]["content"] == last["content"]:
            return base
        return base + [last]
    return incoming
