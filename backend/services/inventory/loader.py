"""Schema bootstrap and bulk load for alert enrichment."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from config import Settings
from services.inventory.constants import INVENTORY_DDL
from services.inventory.converters import (
    asset_record_to_dict,
    relationship_record_to_dict,
    user_record_to_dict,
)
from services.inventory.csv_seed import seed_inventory_from_csv_if_empty
from services.splunk_json_store import ensure_pool, splunk_store_configured


async def ensure_inventory_schema(settings: Settings) -> None:
    pool = await ensure_pool(settings)
    async with pool.acquire() as conn:
        await conn.execute(INVENTORY_DDL)


async def load_inventory_from_postgres(
    settings: Settings,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    from services.inventory.assets import list_assets
    from services.inventory.relationships import list_relationships
    from services.inventory.users import list_users

    users = [user_record_to_dict(r) for r in await list_users(settings)]
    assets = [asset_record_to_dict(r) for r in await list_assets(settings)]
    relationships = [relationship_record_to_dict(r) for r in await list_relationships(settings)]
    return users, assets, relationships
