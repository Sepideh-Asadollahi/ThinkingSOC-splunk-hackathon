"""Read stored TSOC records from PostgreSQL."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from config import Settings

from . import pg
from .pg import init_store, splunk_store_configured

logger = logging.getLogger(__name__)


def _map_stored_row(row: Any) -> Dict[str, Any]:
    pl = row["payload"] if isinstance(row["payload"], dict) else {}
    ri = row["row_index"]
    if ri is None and isinstance(pl, dict) and pl.get("row_index") is not None:
        ri = pl.get("row_index")
    return {
        "id": row["id"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "tsoc_record_type": row["tsoc_record_type"],
        "sid": row["sid"],
        "search_name": row["search_name"],
        "row_index": ri,
        "payload": pl,
    }


async def search_stored_events(
    settings: Settings,
    *,
    sid: Optional[str] = None,
    record_type: Optional[str] = None,
    row_index: Optional[int] = None,
    limit: int = 100,
    earliest: str = "-90d@d",
    order: str = "desc",
) -> List[Dict[str, Any]]:
    """Read stored records from PostgreSQL by optional sid / record_type filters."""
    _ = earliest
    if not splunk_store_configured(settings):
        return []
    if pg._PG_POOL is None:
        await init_store(settings)
    if pg._PG_POOL is None:
        return []

    lim = max(1, min(limit, 500))
    where: List[str] = []
    args: List[Any] = []
    argn = 1
    if sid:
        where.append("sid = ${0}".format(argn))
        args.append(sid)
        argn += 1
    if record_type:
        where.append("tsoc_record_type = ${0}".format(argn))
        args.append(record_type)
        argn += 1
    if row_index is not None:
        where.append("row_index = ${0}".format(argn))
        args.append(int(row_index))
        argn += 1

    where_sql = "WHERE " + " AND ".join(where) if where else ""
    order_sql = "ASC" if str(order).lower() == "asc" else "DESC"
    query = """
        SELECT id, created_at, tsoc_record_type, sid, search_name, row_index, payload
        FROM tsoc_records
        {where}
        ORDER BY created_at {order_sql}
        LIMIT {limit}
    """.format(where=where_sql, order_sql=order_sql, limit=lim)
    async with pg._PG_POOL.acquire() as conn:
        rows = await conn.fetch(query, *args)
    return [_map_stored_row(row) for row in rows]


async def get_stored_event_by_id(
    settings: Settings,
    record_id: int,
) -> Optional[Dict[str, Any]]:
    """Fetch a single stored record by primary key."""
    t0 = time.perf_counter()
    if not splunk_store_configured(settings):
        logger.warning("storage.get_by_id record_id=%s skip postgres_not_configured", record_id)
        return None
    if pg._PG_POOL is None:
        logger.info("storage.get_by_id record_id=%s init_pool", record_id)
        await init_store(settings)
    if pg._PG_POOL is None:
        logger.error("storage.get_by_id record_id=%s pool_still_none after init", record_id)
        return None

    query = """
        SELECT id, created_at, tsoc_record_type, sid, search_name, row_index, payload
        FROM tsoc_records
        WHERE id = $1
        LIMIT 1
    """
    t_query = time.perf_counter()
    async with pg._PG_POOL.acquire() as conn:
        row = await conn.fetchrow(query, int(record_id))
    query_ms = (time.perf_counter() - t_query) * 1000.0
    if row is None:
        logger.info(
            "storage.get_by_id record_id=%s not_found query_ms=%.1f total_ms=%.1f",
            record_id,
            query_ms,
            (time.perf_counter() - t0) * 1000.0,
        )
        return None

    t_map = time.perf_counter()
    mapped = _map_stored_row(row)
    map_ms = (time.perf_counter() - t_map) * 1000.0
    pl = mapped.get("payload") if isinstance(mapped.get("payload"), dict) else {}
    pl_keys = len(pl.keys()) if isinstance(pl, dict) else 0
    logger.info(
        "storage.get_by_id record_id=%s found type=%s query_ms=%.1f map_ms=%.1f "
        "total_ms=%.1f payload_keys=%d",
        record_id,
        mapped.get("tsoc_record_type"),
        query_ms,
        map_ms,
        (time.perf_counter() - t0) * 1000.0,
        pl_keys,
    )
    return mapped
