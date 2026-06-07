"""Statistical intent detection for SOC Chat Text-to-SQL (LLM-only)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from config import Settings
from services.llm.litellm_service import LiteLLMNotConfiguredError, litellm_chat_completion
from services.llm.thinking_content import split_thinking_and_answer

from .prompt_context import format_conversation_for_sql
from .prompts import CLASSIFY_SYSTEM

logger = logging.getLogger(__name__)


def _parse_classify_json(content: str) -> bool:
    _, text = split_thinking_and_answer(content)
    if not text:
        raise ValueError("empty classify response")
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in classify response")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("classify JSON is not an object")
    return bool(data.get("is_statistical"))


async def is_statistical_question(
    settings: Settings,
    question: str,
    *,
    messages: Optional[List[Dict[str, Any]]] = None,
    request_id: Optional[str] = None,
) -> bool:
    """Route to Text-to-SQL when the LLM classifies the question as statistical/list/count."""
    q = (question or "").strip()
    if not q:
        return False

    rid = request_id or "-"
    user_content = format_conversation_for_sql(messages, q)
    try:
        result = await litellm_chat_completion(
            settings,
            [
                {"role": "system", "content": CLASSIFY_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            model=_sql_classify_model(settings),
            temperature=0.0,
            max_tokens=int(settings.tsoc_chat_sql_classify_max_tokens),
        )
        content = str(result.get("content") or "")
        thinking = result.get("thinking")
        if thinking:
            logger.info("soc_sql classify_thinking rid=%s\n%s", rid, thinking)
        is_stat = _parse_classify_json(content)
        logger.info("soc_sql classify rid=%s is_statistical=%s", rid, is_stat)
        return is_stat
    except (LiteLLMNotConfiguredError, json.JSONDecodeError, ValueError) as exc:
        logger.warning("soc_sql classify failed rid=%s err=%s — not routing to SQL", rid, exc)
    return False


def _sql_classify_model(settings: Settings) -> str:
    explicit = (settings.tsoc_chat_sql_model or "").strip()
    if explicit:
        return explicit
    return (settings.litellm_model or "").strip()
