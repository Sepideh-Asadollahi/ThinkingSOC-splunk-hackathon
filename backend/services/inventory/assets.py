"""Asset inventory CRUD."""

from __future__ import annotations

from typing import List

from config import Settings
from models.inventory import AssetCreate, AssetRecord, AssetUpdate
from services.inventory._db import dynamic_update, is_unique_violation, raise_if_delete_missing
from services.inventory.exceptions import InventoryConflictError, InventoryNotFoundError
from services.splunk_json_store import ensure_pool

_ASSET_SELECT = (
    "asset_id, asset_type, hostname, fqdn, ip, owner, criticality, risk_score, description"
)


async def list_assets(settings: Settings) -> List[AssetRecord]:
    pool = await ensure_pool(settings)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT {0} FROM tsoc_assets ORDER BY asset_id".format(_ASSET_SELECT)
        )
    return [AssetRecord(**dict(r)) for r in rows]


async def get_asset(settings: Settings, asset_id: str) -> AssetRecord:
    pool = await ensure_pool(settings)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT {0} FROM tsoc_assets WHERE asset_id = $1".format(_ASSET_SELECT),
            asset_id,
        )
    if row is None:
        raise InventoryNotFoundError("asset not found: {0}".format(asset_id))
    return AssetRecord(**dict(row))


async def create_asset(settings: Settings, body: AssetCreate) -> AssetRecord:
    pool = await ensure_pool(settings)
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tsoc_assets (
                    asset_id, asset_type, hostname, fqdn, ip, owner, criticality, risk_score, description
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                body.asset_id,
                body.asset_type,
                body.hostname,
                body.fqdn,
                body.ip,
                body.owner,
                body.criticality,
                body.risk_score,
                body.description,
            )
    except Exception as e:
        if is_unique_violation(e):
            raise InventoryConflictError("asset_id already exists: {0}".format(body.asset_id)) from e
        raise
    return await get_asset(settings, body.asset_id)


async def update_asset(settings: Settings, asset_id: str, body: AssetUpdate) -> AssetRecord:
    await get_asset(settings, asset_id)
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        return await get_asset(settings, asset_id)
    await dynamic_update(
        settings, table="tsoc_assets", id_column="asset_id", id_value=asset_id, fields=fields
    )
    return await get_asset(settings, asset_id)


async def delete_asset(settings: Settings, asset_id: str) -> None:
    pool = await ensure_pool(settings)
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM tsoc_assets WHERE asset_id = $1", asset_id)
    raise_if_delete_missing(result, "asset", asset_id)
