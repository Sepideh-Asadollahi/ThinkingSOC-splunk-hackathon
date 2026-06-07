"""Load inventory tables from PostgreSQL (or inline JSON for tests)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from config import Settings
from services.inventory import load_inventory_from_postgres
from services.splunk_json_store import splunk_store_configured

logger = logging.getLogger(__name__)


class IncompleteOfflineInventoryError(Exception):
    """Only some of users/assets/relationships were provided."""


async def load_inventory_tables(
    settings: Settings,
    users: Optional[List[Dict[str, Any]]] = None,
    assets: Optional[List[Dict[str, Any]]] = None,
    relationships: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return users, assets, and relationships from inline JSON or PostgreSQL."""
    if users is not None and assets is not None and relationships is not None:
        logger.info(
            "inventory offline users=%d assets=%d relationships=%d",
            len(users),
            len(assets),
            len(relationships),
        )
        return users, assets, relationships
    if users is not None or assets is not None or relationships is not None:
        raise IncompleteOfflineInventoryError(
            "Provide all three of users, assets, and relationships for offline mode, or omit all three."
        )
    if not splunk_store_configured(settings):
        raise ValueError("PostgreSQL not configured; set TSOC_POSTGRES_DSN.")
    users_pg, assets_pg, rels_pg = await load_inventory_from_postgres(settings)
    logger.info(
        "inventory from postgres users=%d assets=%d relationships=%d",
        len(users_pg),
        len(assets_pg),
        len(rels_pg),
    )
    return users_pg, assets_pg, rels_pg
