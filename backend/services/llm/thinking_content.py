"""Split reasoning/thinking from the final model answer in LLM responses."""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple


def _tag(name: str, *, close: bool = False) -> str:
    return "<{0}{1}>".format("/" if close else "", name)


# Build tag strings without embedding raw markup in source (editor-safe).
_REDACTED_OPEN = _tag("redacted_thinking")
_REDACTED_CLOSE = _tag("redacted_thinking", close=True)
_BT = "`"
# DeepSeek / Qwen backtick-wrapped think blocks (not XML)
_THINK_OPEN = _BT * 2 + "think" + _BT * 2
_THINK_CLOSE = _BT * 2 + "/think" + _BT * 2
_THINKING_OPEN = _tag("thinking")
_THINKING_CLOSE = _tag("thinking", close=True)
_BUDGET_OPEN = _tag("budget:thinking")
_BUDGET_CLOSE = _tag("budget:thinking", close=True)

_REDACTED_THINKING_RE = re.compile(
    re.escape(_REDACTED_OPEN) + r"([\s\S]*?)" + re.escape(_REDACTED_CLOSE),
    re.IGNORECASE,
)
_THINKING_TAG_RE = re.compile(
    re.escape(_THINKING_OPEN) + r"([\s\S]*?)" + re.escape(_THINKING_CLOSE),
    re.IGNORECASE,
)
_BUDGET_THINKING_RE = re.compile(
    re.escape(_BUDGET_OPEN) + r"([\s\S]*?)" + re.escape(_BUDGET_CLOSE),
    re.IGNORECASE,
)
_LEGACY_THINK_RE = re.compile(
    re.escape(_THINK_OPEN) + r"([\s\S]*?)" + re.escape(_THINK_CLOSE),
    re.IGNORECASE,
)
# Qwen3: visible answer often starts after the closing `` marker.
_QWEN3_THINK_END = _THINK_CLOSE


def _append_thinking(chunks: List[str], piece: Optional[str]) -> None:
    text = (piece or "").strip()
    if text:
        chunks.append(text)


def _extract_thinking_blocks(thinking_blocks: Any) -> List[str]:
    out: List[str] = []
    if not thinking_blocks:
        return out
    for block in thinking_blocks:
        if not isinstance(block, dict):
            continue
        btype = str(block.get("type") or "").lower()
        if btype == "thinking":
            _append_thinking(out, block.get("thinking"))
        elif btype == "redacted_thinking":
            data = block.get("data")
            if data:
                _append_thinking(out, "[redacted_thinking:{0}]".format(str(data)[:80]))
            else:
                _append_thinking(out, "[redacted_thinking]")
    return out


def _strip_tag_blocks(text: str, chunks: List[str]) -> str:
    """Move known thinking tag regions into *chunks*; return remaining answer text."""
    for pattern in (
        _REDACTED_THINKING_RE,
        _THINKING_TAG_RE,
        _BUDGET_THINKING_RE,
        _LEGACY_THINK_RE,
    ):
        while True:
            m = pattern.search(text)
            if not m:
                break
            _append_thinking(chunks, m.group(1))
            text = (text[: m.start()] + text[m.end() :]).strip()
    return text


def split_thinking_and_answer(
    content: Optional[str],
    *,
    reasoning_content: Optional[str] = None,
    thinking_blocks: Any = None,
) -> Tuple[Optional[str], str]:
    """
    Return (thinking_text, answer_text).

    Handles message.reasoning_content, thinking_blocks, XML thinking tags,
    and Qwen3 `` delimiter (answer follows the closing tag).
    """
    thinking_chunks: List[str] = []
    _append_thinking(thinking_chunks, reasoning_content)
    thinking_chunks.extend(_extract_thinking_blocks(thinking_blocks))

    text = (content or "").strip()

    if _QWEN3_THINK_END in text:
        before, _, after = text.partition(_QWEN3_THINK_END)
        _append_thinking(thinking_chunks, before)
        text = after.strip()

    text = _strip_tag_blocks(text, thinking_chunks)

    thinking = "\n\n".join(thinking_chunks).strip() or None
    answer = text.strip()
    return thinking, answer


def split_litellm_message(message: Any) -> Tuple[Optional[str], str]:
    """Split a LiteLLM/OpenAI choice.message object into thinking + answer."""
    reasoning_content = getattr(message, "reasoning_content", None)
    if reasoning_content is None:
        reasoning_content = getattr(message, "reasoning", None)

    thinking_blocks = getattr(message, "thinking_blocks", None)
    provider_fields = getattr(message, "provider_specific_fields", None) or {}
    if isinstance(provider_fields, dict):
        if reasoning_content is None:
            reasoning_content = provider_fields.get("reasoning_content")
        if thinking_blocks is None:
            thinking_blocks = provider_fields.get("thinking_blocks")

    content = getattr(message, "content", None)
    if isinstance(content, list):
        thinking_chunks: List[str] = []
        answer_chunks: List[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = str(block.get("type") or "").lower()
            if btype in ("thinking", "redacted_thinking"):
                if btype == "thinking":
                    _append_thinking(thinking_chunks, block.get("thinking"))
                else:
                    _append_thinking(thinking_chunks, "[redacted_thinking]")
            elif btype == "text":
                piece = block.get("text")
                if piece:
                    answer_chunks.append(str(piece))
        extra_thinking, joined = split_thinking_and_answer(
            "\n".join(answer_chunks) if answer_chunks else None,
            reasoning_content=str(reasoning_content) if reasoning_content else None,
            thinking_blocks=thinking_blocks,
        )
        parts = [p for p in ["\n\n".join(thinking_chunks) if thinking_chunks else None, extra_thinking] if p]
        merged_thinking = "\n\n".join(parts).strip() or None
        return merged_thinking, joined

    return split_thinking_and_answer(
        str(content) if content is not None else None,
        reasoning_content=str(reasoning_content) if reasoning_content else None,
        thinking_blocks=thinking_blocks,
    )
