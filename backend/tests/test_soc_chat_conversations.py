"""Tests for SOC chat conversation persistence and session RAG helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from services.soc_rag.chat_history import build_conversation_context
from services.soc_rag.chat_store import merge_request_messages
from services.soc_rag.models import SocChatMessage


def test_merge_request_messages_appends_new_user() -> None:
    stored = [{"role": "user", "content": "hello", "seq": 1}]
    incoming = [SocChatMessage(role="user", content="follow up")]
    merged = merge_request_messages(stored, incoming)
    assert merged == [
        {"role": "user", "content": "hello"},
        {"role": "user", "content": "follow up"},
    ]


def test_merge_request_messages_uses_full_client_history() -> None:
    stored = [
        {"role": "user", "content": "a", "seq": 1},
        {"role": "assistant", "content": "b", "seq": 2},
    ]
    incoming = [
        SocChatMessage(role="user", content="a"),
        SocChatMessage(role="assistant", content="b"),
        SocChatMessage(role="user", content="c"),
    ]
    merged = merge_request_messages(stored, incoming)
    assert [m["content"] for m in merged] == ["a", "b", "c"]


def test_build_conversation_context_short_thread() -> None:
    class _Settings:
        tsoc_chat_history_direct_max = 12
        tsoc_chat_history_rag_top_k = 8
        tsoc_chat_history_recent_tail = 4

    messages = [{"role": "user", "content": "one"}, {"role": "assistant", "content": "two"}]
    text = build_conversation_context(_Settings(), messages=messages, question="three")
    assert "one" in text and "two" in text
    assert "session RAG" not in text


def test_build_conversation_context_long_thread_uses_rag() -> None:
    class _Settings:
        tsoc_chat_history_direct_max = 4
        tsoc_chat_history_rag_top_k = 2
        tsoc_chat_history_recent_tail = 2

    messages = [{"role": "user", "content": f"msg-{i}"} for i in range(8)]
    session_hits = [({"role": "user", "content": "msg-1", "seq": 1}, 0.9)]
    text = build_conversation_context(
        _Settings(),
        messages=messages,
        question="latest",
        session_hits=session_hits,
    )
    assert "session RAG" in text
    assert "msg-1" in text


async def test_resolve_empty_conversation_does_not_recreate() -> None:
    """Existing conversation with zero messages must not trigger duplicate INSERT."""
    from config import get_settings
    from services.soc_rag.chat import _resolve_conversation_messages
    from services.soc_rag.models import SocChatRequest

    settings = get_settings()
    cid = "conv-existing-empty"
    body = SocChatRequest(
        conversation_id=cid,
        messages=[SocChatMessage(role="user", content="hello")],
    )

    with (
        patch(
            "services.soc_rag.chat.get_or_create_conversation",
            new_callable=AsyncMock,
            return_value={"conversation_id": cid, "message_count": 0},
        ) as get_or_create,
        patch(
            "services.soc_rag.chat.load_conversation_messages",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch("services.soc_rag.chat.create_conversation", new_callable=AsyncMock) as create,
    ):
        out_cid, merged = await _resolve_conversation_messages(settings, body, request_id="t")

    assert out_cid == cid
    assert merged == [{"role": "user", "content": "hello"}]
    get_or_create.assert_awaited_once_with(settings, cid)
    create.assert_not_awaited()
