"""Natural-language answers from SQL query results."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from config import Settings
from services.llm.litellm_service import LiteLLMNotConfiguredError, litellm_chat_completion

from .generate import _sql_generation_model
from .prompt_context import format_conversation_for_sql
from .prompts import ANSWER_SYSTEM

logger = logging.getLogger(__name__)

_REASONING_LEAK_RE = re.compile(
    r"(?i)^\s*(?:okay|ok),?\s+let'?s\s+see|let me think|first,?\s+i need to",
)
_COUNT_KEYS = ("cnt", "count", "total_count", "user_count", "asset_count")
_NAME_KEYS = (
    "display_name",
    "title",
    "search_name",
    "summary_line",
    "display_id",
    "user_id",
    "asset_id",
    "hostname",
    "email",
)


def _table_label(tables_used: Optional[List[str]]) -> str:
    if tables_used:
        return ", ".join(tables_used)
    return "the database"


def _row_display_line(row: Dict[str, Any]) -> str:
    """One human-readable line per SQL row (no raw JSON)."""
    name: Optional[str] = None
    for key in _NAME_KEYS:
        val = row.get(key)
        if val is not None and str(val).strip():
            name = str(val).strip()
            break
    sid = row.get("sid")
    sid_s = str(sid).strip() if sid is not None else ""
    rtype = row.get("tsoc_record_type") or row.get("doc_type")
    rtype_s = str(rtype).strip() if rtype else ""

    display_id = row.get("display_id")
    display_id_s = str(display_id).strip() if display_id is not None else ""

    if name and display_id_s and display_id_s not in name:
        line = "{0} — {1}".format(display_id_s, name)
    elif name and sid_s:
        line = "{0} (sid={1})".format(name, sid_s)
    elif name:
        line = name
    elif display_id_s:
        line = display_id_s
    elif sid_s:
        line = "sid={0}".format(sid_s)
    else:
        line = "record"

    if rtype_s:
        line = "{0} [{1}]".format(line, rtype_s)
    finding_type = row.get("finding_type")
    if finding_type is not None and str(finding_type).strip() and not rtype_s:
        line = "{0} [{1}]".format(line, finding_type)
    priority = row.get("investigation_priority")
    if priority is not None and str(priority).strip():
        line = "{0} | priority={1}".format(line, priority)
    risk = row.get("risk_score")
    if risk is not None:
        line = "{0} | risk={1}".format(line, risk)
    score = row.get("triage_score")
    if score is not None:
        line = "{0} | score={1}".format(line, score)
    return line


def _is_simple_result_set(rows: List[Dict[str, Any]]) -> bool:
    """Count/list answers — format locally; skip slow answer LLM."""
    return not rows or len(rows) <= 50


def format_answer_from_rows(
    question: str,
    rows: List[Dict[str, Any]],
    *,
    tables_used: Optional[List[str]] = None,
) -> str:
    """Format SQL rows for the user (fast path; also fallback if answer LLM fails)."""
    table = _table_label(tables_used)
    q = (question or "").lower()

    if not rows:
        if "alert" in q:
            return (
                "There are **0** items on the Analysis queue "
                "(no soc_analysis / observability_analysis rows in storage)."
            )
        return "The query returned no rows."

    if len(rows) == 1:
        row = rows[0]
        for key in _COUNT_KEYS:
            if key in row and row[key] is not None:
                n = int(row[key])
                if "alert" in q:
                    return "There are **{0}** alert(s) on the Analysis queue.".format(n)
                return "Count: **{0}**.".format(n)

    if len(rows) <= 50:
        lines: List[str] = []
        total: Optional[int] = None
        if rows and "total_count" in rows[0]:
            try:
                total = int(rows[0]["total_count"])
            except (TypeError, ValueError):
                total = None
        if total is not None:
            if "alert" in q:
                lines.append("There are **{0}** alert(s) on the Analysis queue:".format(total))
            else:
                lines.append("Total: **{0}**.".format(total))
        else:
            lines.append("**{0}** result(s):".format(len(rows)))
        for i, row in enumerate(rows[:20], 1):
            lines.append("{0}. {1}".format(i, _row_display_line(row)))
        if len(rows) > 20:
            lines.append("… and {0} more.".format(len(rows) - 20))
        return "\n".join(lines)

    return "**{0}** rows returned (too many to list here).".format(len(rows))


def _looks_like_reasoning_leak(text: str) -> bool:
    return bool(_REASONING_LEAK_RE.search(text or ""))


async def synthesize_answer(
    settings: Settings,
    question: str,
    rows: List[Dict[str, Any]],
    *,
    tables_used: Optional[List[str]] = None,
    sql: Optional[str] = None,
    messages: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Format answer from SQL rows.

    Simple count/list (≤50 rows): format locally — instant, no extra LLM call.
    Large/complex result sets: optional LLM with a modest token cap.
    """
    direct = format_answer_from_rows(question, rows, tables_used=tables_used)
    if _is_simple_result_set(rows):
        logger.info("soc_sql answer_direct tables=%s\n%s", tables_used, direct)
        return direct

    model = _sql_generation_model(settings)
    max_tokens = min(
        int(settings.tsoc_chat_sql_answer_max_tokens),
        2048,
    )
    payload = json.dumps(
        {
            "tables_queried": tables_used or [],
            "row_count": len(rows),
            "sample_rows": rows[:10],
        },
        ensure_ascii=False,
        default=str,
    )
    user_content = (
        "{0}\n\nTables queried: {1}\n\nQuery results (sample):\n{2}"
    ).format(
        format_conversation_for_sql(messages, question),
        _table_label(tables_used),
        payload,
    )

    try:
        logger.info("soc_sql answer_prompt model=%s role=system\n%s", model, ANSWER_SYSTEM)
        logger.info("soc_sql answer_prompt model=%s role=user\n%s", model, user_content)
        result = await litellm_chat_completion(
            settings,
            [
                {"role": "system", "content": ANSWER_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            model=model,
            temperature=0.0,
            max_tokens=max_tokens,
        )
        answer = str(result.get("content") or "").strip()
        thinking = result.get("thinking")
        if thinking:
            logger.info("soc_sql answer_thinking\n%s", thinking)
        logger.info("soc_sql answer_response\n%s", answer)

        if answer and not _looks_like_reasoning_leak(answer):
            return answer
    except LiteLLMNotConfiguredError:
        logger.warning("soc_sql answer_llm_not_configured — using direct formatter")
    except Exception as exc:
        logger.warning("soc_sql answer_llm_failed err=%s — using direct formatter", exc)

    logger.info("soc_sql answer_fallback tables=%s\n%s", tables_used, direct)
    return direct
