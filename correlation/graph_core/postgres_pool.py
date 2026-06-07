from __future__ import annotations

import json
import logging
from typing import Any, Optional

import asyncpg

from correlation_config import Settings, get_settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


def _postgres_dsn(settings: Settings) -> str:
    return (
        (getattr(settings, "tsoc_postgres_dsn", None) or getattr(settings, "correlation_postgres_dsn", None) or "")
        .strip()
    )


def discard_pool() -> None:
    """Drop pool reference without closing (safe when event loop may have changed)."""
    global _pool
    _pool = None


async def init_pool(settings: Optional[Settings] = None) -> Optional[asyncpg.Pool]:
    global _pool
    s = settings or get_settings()
    dsn = _postgres_dsn(s)
    if not dsn:
        return None
    if _pool is not None:
        return _pool
    _pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def reset_pool() -> None:
    global _pool
    if _pool is None:
        return
    try:
        await _pool.close()
    except RuntimeError:
        pass
    _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("PostgreSQL pool not initialized")
    return _pool


async def verify_connectivity(settings: Optional[Settings] = None) -> bool:
    s = settings or get_settings()
    dsn = _postgres_dsn(s)
    if not dsn:
        return False
    try:
        conn = await asyncpg.connect(dsn=dsn, timeout=5)
        try:
            await conn.fetchval("SELECT 1")
            return True
        finally:
            await conn.close()
    except Exception as exc:
        logger.warning("postgres connectivity failed: %s", exc)
        return False


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


async def execute_sql_file(path: str, *, settings: Optional[Settings] = None) -> None:
    from pathlib import Path

    s = settings or get_settings()
    dsn = _postgres_dsn(s)
    if not dsn:
        raise RuntimeError("TSOC_POSTGRES_DSN not set")
    sql = Path(path).read_text(encoding="utf-8")
    conn = await asyncpg.connect(dsn=dsn)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()
