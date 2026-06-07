"""Shared PostgreSQL helpers for inventory CRUD."""

from __future__ import annotations

from typing import Any, Dict

from config import Settings
from services.inventory.exceptions import InventoryNotFoundError
from services.splunk_json_store import ensure_pool


def is_unique_violation(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "unique" in msg or "duplicate" in msg


def raise_if_delete_missing(result: str, entity: str, entity_id: str) -> None:
    if result == "DELETE 0":
        raise InventoryNotFoundError("{0} not found: {1}".format(entity, entity_id))


async def dynamic_update(
    settings: Settings,
    *,
    table: str,
    id_column: str,
    id_value: str,
    fields: Dict[str, Any],
) -> None:
    sets = ", ".join("{0} = ${1}".format(k, i + 2) for i, k in enumerate(fields))
    values = list(fields.values())
    pool = await ensure_pool(settings)
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE {0} SET {1}, updated_at = now() WHERE {2} = $1".format(table, sets, id_column),
            id_value,
            *values,
        )
