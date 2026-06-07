"""PostgreSQL pool, schema bootstrap, and JSONB insert helpers."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from config import Settings

logger = logging.getLogger(__name__)
_PG_POOL: Any = None


def jsonb_param(value: Any) -> str:
    """Serialize for asyncpg JSONB bind ($n::jsonb expects a JSON string)."""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


async def _init_pg_connection(conn: Any) -> None:
    await conn.set_type_codec(
        "jsonb",
        schema="pg_catalog",
        encoder=jsonb_param,
        decoder=json.loads,
        format="text",
    )
    await conn.set_type_codec(
        "json",
        schema="pg_catalog",
        encoder=jsonb_param,
        decoder=json.loads,
        format="text",
    )


def splunk_store_configured(settings: Settings) -> bool:
    dsn = (settings.tsoc_postgres_dsn or "").strip()
    return bool(dsn)


async def init_store(settings: Settings) -> None:
    """Initialize PostgreSQL pool and create storage table when configured."""
    global _PG_POOL
    if not splunk_store_configured(settings):
        logger.info("postgres_store init skipped: TSOC_POSTGRES_DSN not configured")
        return
    if _PG_POOL is not None:
        return
    try:
        import asyncpg

        from services.demo.postgres_snapshot import restore_postgres_snapshot_if_empty
        from services.inventory.csv_seed import ensure_default_relationships
        from services.inventory import ensure_inventory_schema, seed_inventory_from_csv_if_empty

        _PG_POOL = await asyncpg.create_pool(
            dsn=settings.tsoc_postgres_dsn.strip(),
            min_size=1,
            max_size=10,
            init=_init_pg_connection,
        )
        async with _PG_POOL.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tsoc_records (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    tsoc_record_type TEXT NOT NULL,
                    sid TEXT NULL,
                    search_name TEXT NULL,
                    row_index INTEGER NULL,
                    payload JSONB NOT NULL
                );
                """
            )
            # Existing deployments may predate row_index; add column before any index on it.
            await conn.execute(
                "ALTER TABLE tsoc_records ADD COLUMN IF NOT EXISTS row_index INTEGER NULL"
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tsoc_records_type_created
                    ON tsoc_records (tsoc_record_type, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_tsoc_records_sid_created
                    ON tsoc_records (sid, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_tsoc_records_sid_row_created
                    ON tsoc_records (sid, row_index, created_at DESC);
                """
            )
        await ensure_inventory_schema(settings)
        restored = await restore_postgres_snapshot_if_empty(settings)
        if not restored:
            await seed_inventory_from_csv_if_empty(settings)
            await ensure_default_relationships(settings)
        logger.info("postgres_store initialized")
    except Exception as e:
        logger.warning("postgres_store init failed: %s", e, exc_info=True)
        raise


async def close_store() -> None:
    global _PG_POOL
    if _PG_POOL is None:
        return
    try:
        await _PG_POOL.close()
    finally:
        _PG_POOL = None


async def ensure_pool(settings: Settings) -> Any:
    """Return the shared asyncpg pool, initializing schema if needed."""
    if not splunk_store_configured(settings):
        raise ValueError("PostgreSQL store not configured; set TSOC_POSTGRES_DSN.")
    await init_store(settings)
    if _PG_POOL is None:
        raise RuntimeError("postgres_store pool is not initialized")
    return _PG_POOL


async def submit_hec_event(settings: Settings, event: Dict[str, Any], **_: Any) -> bool:
    """Backward-compatible name: persist one event into PostgreSQL store."""
    if not splunk_store_configured(settings):
        return False
    if _PG_POOL is None:
        await init_store(settings)
    if _PG_POOL is None:
        return False
    rec_type = str(event.get("tsoc_record_type") or "unknown")
    sid = event.get("sid")
    search_name = event.get("search_name")
    row_index = event.get("row_index")
    if row_index is not None:
        row_index = int(row_index)
    try:
        async with _PG_POOL.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tsoc_records (tsoc_record_type, sid, search_name, row_index, payload)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                """,
                rec_type,
                sid,
                search_name,
                row_index,
                jsonb_param(event),
            )
        return True
    except Exception as e:
        logger.warning("postgres_store insert failed type=%s sid=%s err=%s", rec_type, sid, e, exc_info=True)
        return False
