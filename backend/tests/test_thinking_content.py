"""Tests for thinking vs answer separation."""

from __future__ import annotations

from services.llm.thinking_content import (
    _REDACTED_CLOSE,
    _REDACTED_OPEN,
    _THINK_CLOSE,
    split_thinking_and_answer,
)


def test_redacted_thinking_tags() -> None:
    raw = (
        _REDACTED_OPEN
        + "Reasoning about alerts."
        + _REDACTED_CLOSE
        + "\n"
        '{"sql":"SELECT 1","tables_used":["tsoc_users"]}'
    )
    thinking, answer = split_thinking_and_answer(raw)
    assert thinking is not None
    assert "Reasoning" in thinking
    assert "SELECT 1" in answer


def test_reasoning_content_field() -> None:
    thinking, answer = split_thinking_and_answer(
        '{"sql":"SELECT COUNT(*)::int AS cnt FROM tsoc_users","tables_used":["tsoc_users"]}',
        reasoning_content="Internal chain of thought.",
    )
    assert thinking == "Internal chain of thought."
    assert "SELECT COUNT" in answer


def test_qwen3_backtick_delimiter() -> None:
    raw = "Let me count alerts.{0}\n{{\"sql\":\"SELECT 1\",\"tables_used\":[]}}".format(_THINK_CLOSE)
    thinking, answer = split_thinking_and_answer(raw)
    assert thinking is not None
    assert "alerts" in thinking.lower()
    assert "sql" in answer.lower()
