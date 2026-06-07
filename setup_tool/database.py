"""PostgreSQL schema application."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Dict, List

from setup_tool.log import LOG
from setup_tool.paths import EXPECTED_TABLES, SCHEMA_SQL
from setup_tool.retry_util import retry_async, step_attempts


def split_sql_statements(sql: str) -> List[str]:
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    parts: List[str] = []
    for chunk in sql.split(";"):
        stmt = chunk.strip()
        if not stmt:
            continue
        if stmt.upper() in ("BEGIN", "COMMIT", "ROLLBACK"):
            continue
        parts.append(stmt + ";")
    return parts


async def _connect_postgres(dsn: str):
    import asyncpg

    return await asyncpg.connect(dsn=dsn, timeout=30)


async def apply_schema_async(dsn: str) -> bool:
    LOG.info("[DATABASE] Connecting … (up to %s attempts)", step_attempts())
    conn = await retry_async("postgres connect", lambda: _connect_postgres(dsn))
    try:
        if not SCHEMA_SQL.is_file():
            LOG.error("[DATABASE] Missing %s", SCHEMA_SQL)
            return False
        statements = split_sql_statements(SCHEMA_SQL.read_text(encoding="utf-8"))
        LOG.info("[DATABASE] Applying %s (%d statements)", SCHEMA_SQL.name, len(statements))
        for i, stmt in enumerate(statements, 1):
            LOG.debug("[DATABASE]   [%d/%d] %s", i, len(statements), stmt.split("\n", 1)[0][:70])
            await conn.execute(stmt)
        rows = await conn.fetch(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        )
        present = {r["table_name"] for r in rows}
        missing = [t for t in EXPECTED_TABLES if t not in present]
        if missing:
            LOG.error("[DATABASE] Missing tables: %s", ", ".join(missing))
            return False
        LOG.info("[DATABASE] OK — tables: %s", ", ".join(EXPECTED_TABLES))
        return True
    finally:
        await conn.close()


def step_database(env: Dict[str, str], apply_schema: bool) -> bool:
    dsn = (env.get("TSOC_POSTGRES_DSN") or "").strip()
    if not dsn:
        LOG.error("[DATABASE] No DSN")
        return False
    if not apply_schema:
        LOG.info("[DATABASE] Skipped (--skip-schema)")
        return True
    try:
        return asyncio.run(apply_schema_async(dsn))
    except Exception as e:
        LOG.error("[DATABASE] %s", e, exc_info=LOG.isEnabledFor(logging.DEBUG))
        return False
