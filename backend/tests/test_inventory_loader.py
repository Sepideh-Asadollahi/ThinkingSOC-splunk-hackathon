"""Inventory loader reads PostgreSQL only."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import asyncio

from config import Settings
from services.inventory.inventory_loader import load_inventory_tables


def test_load_inventory_tables_from_postgres() -> None:
    async def _run() -> None:
        settings = Settings(tsoc_postgres_dsn="postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc")
        with patch(
            "services.inventory.inventory_loader.load_inventory_from_postgres",
            new_callable=AsyncMock,
        ) as m:
            m.return_value = (
                [{"user_id": "u1"}],
                [{"asset_id": "a1"}],
                [{"relationship_id": "rel-1"}],
            )
            users, assets, relationships = await load_inventory_tables(settings, None, None, None)
        assert users[0]["user_id"] == "u1"
        assert assets[0]["asset_id"] == "a1"
        assert relationships[0]["relationship_id"] == "rel-1"
        m.assert_awaited_once()

    asyncio.run(_run())
