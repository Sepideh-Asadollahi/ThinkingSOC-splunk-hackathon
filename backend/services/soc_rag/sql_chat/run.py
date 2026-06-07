"""Orchestrate SOC Chat Text-to-SQL pipeline."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from config import Settings
from services.llm.litellm_service import LiteLLMNotConfiguredError

from ..models import SocChatFilters, SocChatResponse, SocChatSqlMeta
from .answer import synthesize_answer
from .enrich import enrich_rows_with_triage
from .execute import execute_sql
from .generate import generate_sql
from .validator import validate_readonly_sql

logger = logging.getLogger(__name__)


async def run_soc_sql_chat(
    settings: Settings,
    question: str,
    *,
    messages: Optional[List[Dict[str, Any]]] = None,
    filters: Optional[SocChatFilters] = None,
    request_id: Optional[str] = None,
) -> SocChatResponse:
    """Answer a statistical question via Text-to-SQL."""
    rid = request_id or "-"
    t0 = time.perf_counter()

    if not settings.tsoc_chat_sql_enable:
        raise ValueError("SOC chat SQL path is disabled")

    logger.info("soc_sql start rid=%s question_len=%d", rid, len(question))
    logger.info("soc_sql question rid=%s\n%s", rid, question)

    t_gen = time.perf_counter()
    raw_sql, tables_used = await generate_sql(
        settings,
        question,
        filters,
        messages=messages,
    )
    gen_ms = (time.perf_counter() - t_gen) * 1000.0

    safe_sql = validate_readonly_sql(
        raw_sql,
        max_rows=settings.tsoc_chat_sql_max_rows,
    )
    logger.info(
        "soc_sql generated rid=%s gen_ms=%.1f tables=%s raw_sql=%r safe_sql=%r",
        rid,
        gen_ms,
        tables_used,
        raw_sql,
        safe_sql,
    )

    t_exec = time.perf_counter()
    rows = await execute_sql(
        settings,
        safe_sql,
        timeout_seconds=settings.tsoc_chat_sql_timeout_seconds,
        request_id=rid,
    )
    exec_ms = (time.perf_counter() - t_exec) * 1000.0
    logger.info("soc_sql executed rid=%s exec_ms=%.1f row_count=%d", rid, exec_ms, len(rows))

    rows = await enrich_rows_with_triage(
        settings,
        rows,
        tables_used=tables_used,
    )

    t_ans = time.perf_counter()
    try:
        answer = await synthesize_answer(
            settings,
            question,
            rows,
            tables_used=tables_used,
            sql=safe_sql,
            messages=messages,
        )
    except LiteLLMNotConfiguredError:
        if rows:
            answer = "Query results:\n{0}".format(
                json.dumps(rows, ensure_ascii=False, indent=2, default=str)
            )
        else:
            answer = "No rows returned."
    ans_ms = (time.perf_counter() - t_ans) * 1000.0

    total_ms = (time.perf_counter() - t0) * 1000.0
    logger.info(
        "soc_sql done rid=%s total_ms=%.1f answer=%r",
        rid,
        total_ms,
        answer,
    )

    sql_meta = SocChatSqlMeta(
        query_mode="sql",
        sql=safe_sql,
        row_count=len(rows),
        tables_used=tables_used or None,
    )
    return SocChatResponse(
        answer=answer,
        citations=[],
        splunk_mcp_used=False,
        retrieval_backend="postgres",
        retrieval_meta={
            "query_mode": "sql",
            "question": question[:200],
            "gen_ms": round(gen_ms, 1),
            "exec_ms": round(exec_ms, 1),
            "ans_ms": round(ans_ms, 1),
        },
        sql_meta=sql_meta,
    )
