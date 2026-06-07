"""LLM SQL generation and response parsing (LLM-only — no heuristic SQL)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from config import Settings
from services.llm.litellm_service import litellm_chat_completion

from ..models import SocChatFilters
from services.llm.thinking_content import split_thinking_and_answer

from .prompt_context import format_conversation_for_sql
from .prompts import SQL_GEN_SYSTEM

_SQL_FENCE_RE = re.compile(r"```(?:sql)?\s*([\s\S]*?)```", re.IGNORECASE)
_THINKING_MODEL_RE = re.compile(r"thinking", re.IGNORECASE)
logger = logging.getLogger(__name__)


def _balanced_json_spans(text: str) -> List[str]:
    """Return all top-level balanced {...} substrings, respecting string literals."""
    spans: List[str] = []
    depth = 0
    in_str = False
    escape = False
    start = -1
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    spans.append(text[start : i + 1])
                    start = -1
    return spans


def parse_sql_generation(content: str) -> Tuple[str, List[str]]:
    _, text = split_thinking_and_answer(content)
    if not text:
        raise ValueError("empty LLM response")

    for span in reversed(_balanced_json_spans(text)):
        try:
            data = json.loads(span)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        sql = str(data.get("sql") or "").strip()
        if sql:
            tables = data.get("tables_used") or []
            return sql, [str(t) for t in tables]

    m = _SQL_FENCE_RE.search(text)
    if m:
        return m.group(1).strip(), []

    if text.upper().startswith("SELECT"):
        return text, []

    raise ValueError("could not parse SQL from LLM response")


def _format_filter_hints(filters: Optional[SocChatFilters]) -> str:
    if not filters:
        return ""
    bits: List[str] = []
    if filters.severity:
        bits.append("severity filter: {0}".format(filters.severity))
    if filters.lookback_days:
        bits.append("lookback_days: {0}".format(filters.lookback_days))
    if filters.search_name_prefix:
        bits.append("search_name_prefix: {0}".format(filters.search_name_prefix))
    if filters.doc_types:
        bits.append("doc_types: {0}".format(filters.doc_types))
    if not bits:
        return ""
    return "\n\nOptional filters: " + "; ".join(bits)


def _sql_generation_model(settings: Settings) -> str:
    """Model for Text-to-SQL — avoid reasoning/thinking models that never emit JSON."""
    explicit = (settings.tsoc_chat_sql_model or "").strip()
    if explicit:
        return explicit
    main = (settings.litellm_model or "").strip()
    if _THINKING_MODEL_RE.search(main):
        derived = _THINKING_MODEL_RE.sub("instruct", main, count=1)
        if derived != main:
            logger.info(
                "soc_sql derived non-thinking model=%r from litellm_model=%r "
                "(set TSOC_CHAT_SQL_MODEL to override)",
                derived,
                main,
            )
            return derived
    return main


async def _llm_generate_sql(
    settings: Settings,
    user: str,
    *,
    model: str,
    max_tokens: int,
) -> Tuple[str, List[str]]:
    logger.info("soc_sql gen_prompt model=%s role=system\n%s", model, SQL_GEN_SYSTEM)
    logger.info("soc_sql gen_prompt model=%s role=user\n%s", model, user)
    result = await litellm_chat_completion(
        settings,
        [
            {"role": "system", "content": SQL_GEN_SYSTEM},
            {"role": "user", "content": user},
        ],
        model=model,
        temperature=0.0,
        max_tokens=max_tokens,
    )
    content = str(result.get("content") or "")
    thinking = result.get("thinking")
    finish_reason = result.get("finish_reason")
    if thinking:
        logger.info(
            "soc_sql llm_thinking model=%s finish_reason=%s thinking_chars=%d\n%s",
            model,
            finish_reason,
            len(str(thinking)),
            thinking,
        )
    try:
        return parse_sql_generation(content)
    except ValueError as exc:
        logger.warning(
            "soc_sql parse_failed error=%s model=%s finish_reason=%s thinking_chars=%s\nanswer:\n%s",
            exc,
            model,
            finish_reason,
            len(str(thinking)) if thinking else 0,
            content,
        )
        raise


async def generate_sql(
    settings: Settings,
    question: str,
    filters: Optional[SocChatFilters],
    *,
    messages: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[str]]:
    """Generate SQL via LLM only (table choice + count/list/limit from schema guide)."""
    user = format_conversation_for_sql(messages, question) + _format_filter_hints(filters)
    model = _sql_generation_model(settings)
    sql_max_tokens = int(settings.tsoc_chat_sql_max_tokens)

    try:
        return await _llm_generate_sql(
            settings,
            user,
            model=model,
            max_tokens=sql_max_tokens,
        )
    except ValueError:
        pass

    retry_user = (
        "Output a single JSON object on one line, then stop. Schema:\n"
        '{{"sql":"SELECT ...","tables_used":["table_name"]}}\n\n'
        "Question:\n{0}"
    ).format(user)
    return await _llm_generate_sql(
        settings,
        retry_user,
        model=model,
        max_tokens=sql_max_tokens,
    )
