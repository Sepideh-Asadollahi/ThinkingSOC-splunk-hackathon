"""PostgreSQL execution for SOC Chat Text-to-SQL."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from config import Settings
from services.splunk_json_store import pg
from services.splunk_json_store.pg import init_store, splunk_store_configured

logger = logging.getLogger(__name__)


def rows_to_jsonable(rows: List[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        item: Dict[str, Any] = {}
        for key in row.keys():
            val = row[key]
            if hasattr(val, "isoformat"):
                item[key] = val.isoformat()
            else:
                item[key] = val
        out.append(item)
    return out


async def execute_sql(
    settings: Settings,
    sql: str,
    *,
    timeout_seconds: float,
    request_id: str = "-",
) -> List[Dict[str, Any]]:
    if not splunk_store_configured(settings):
        raise RuntimeError("PostgreSQL is not configured")
    if pg._PG_POOL is None:
        await init_store(settings)
    if pg._PG_POOL is None:
        raise RuntimeError("PostgreSQL pool unavailable")

    timeout_ms = int(max(timeout_seconds, 1.0) * 1000)
    logger.info(
        "soc_sql db_execute_start rid=%s timeout_ms=%d sql=%r",
        request_id,
        timeout_ms,
        sql,
    )
    async with pg._PG_POOL.acquire() as conn:
        await conn.execute("SET statement_timeout = {0}".format(timeout_ms))
        try:
            rows = await conn.fetch(sql)
        finally:
            await conn.execute("RESET statement_timeout")
    json_rows = rows_to_jsonable(rows)
    logger.info(
        "soc_sql db_execute_done rid=%s row_count=%d rows=%s",
        request_id,
        len(json_rows),
        json.dumps(json_rows, ensure_ascii=False, default=str),
    )
    return json_rows
