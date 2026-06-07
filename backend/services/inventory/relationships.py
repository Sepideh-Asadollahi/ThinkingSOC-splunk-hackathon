"""User–asset relationship CRUD."""

from __future__ import annotations

from typing import Any, List

from config import Settings
from models.inventory import RelationshipCreate, RelationshipRecord, RelationshipUpdate
from services.inventory._db import dynamic_update, is_unique_violation, raise_if_delete_missing
from services.inventory.exceptions import InventoryConflictError, InventoryNotFoundError
from services.splunk_json_store import ensure_pool

_REL_SELECT = """
    relationship_id, user_id, asset_id, description
"""


def relationship_record_from_row(row: Any) -> RelationshipRecord:
    d = dict(row)
    return RelationshipRecord(
        relationship_id=d["relationship_id"],
        user_id=d["user_id"],
        asset_id=d["asset_id"],
        description=d.get("description"),
    )


async def list_relationships(settings: Settings) -> List[RelationshipRecord]:
    pool = await ensure_pool(settings)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT {0} FROM tsoc_relationships ORDER BY user_id ASC, asset_id ASC".format(_REL_SELECT)
        )
    return [relationship_record_from_row(r) for r in rows]


async def get_relationship(settings: Settings, relationship_id: str) -> RelationshipRecord:
    pool = await ensure_pool(settings)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT {0} FROM tsoc_relationships WHERE relationship_id = $1".format(_REL_SELECT),
            relationship_id,
        )
    if row is None:
        raise InventoryNotFoundError("relationship not found: {0}".format(relationship_id))
    return relationship_record_from_row(row)


async def create_relationship(settings: Settings, body: RelationshipCreate) -> RelationshipRecord:
    pool = await ensure_pool(settings)
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tsoc_relationships (
                    relationship_id, user_id, asset_id, description
                ) VALUES ($1, $2, $3, $4)
                """,
                body.relationship_id,
                body.user_id,
                body.asset_id,
                body.description,
            )
    except Exception as e:
        if is_unique_violation(e):
            raise InventoryConflictError(
                "relationship_id or user+asset pair already exists: {0}".format(body.relationship_id)
            ) from e
        raise
    return await get_relationship(settings, body.relationship_id)


async def update_relationship(
    settings: Settings, relationship_id: str, body: RelationshipUpdate
) -> RelationshipRecord:
    await get_relationship(settings, relationship_id)
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        return await get_relationship(settings, relationship_id)
    await dynamic_update(
        settings,
        table="tsoc_relationships",
        id_column="relationship_id",
        id_value=relationship_id,
        fields=fields,
    )
    return await get_relationship(settings, relationship_id)


async def delete_relationship(settings: Settings, relationship_id: str) -> None:
    pool = await ensure_pool(settings)
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM tsoc_relationships WHERE relationship_id = $1",
            relationship_id,
        )
    raise_if_delete_missing(result, "relationship", relationship_id)
