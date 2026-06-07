"""Load demo inventory from backend/data/demo CSV files."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List

from config import Settings
from models.inventory import AssetCreate, RelationshipCreate, UserCreate
from services.inventory.constants import DEMO_DATA_DIR
from services.inventory.default_relationships import (
    build_default_relationships,
    merge_relationship_lists,
)
from services.splunk_json_store import ensure_pool

logger = logging.getLogger(__name__)


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def iter_demo_csv_paths(filename: str) -> List[Path]:
    """Root demo CSV first, then each scenario subdirectory (sorted by name)."""
    paths: List[Path] = []
    root = DEMO_DATA_DIR / filename
    if root.is_file():
        paths.append(root)
    if DEMO_DATA_DIR.is_dir():
        for subdir in sorted(p for p in DEMO_DATA_DIR.iterdir() if p.is_dir()):
            candidate = subdir / filename
            if candidate.is_file():
                paths.append(candidate)
    return paths


def _dedupe_rows(rows: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    for row in rows:
        row_key = str(row.get(key) or "").strip()
        if not row_key or row_key in seen:
            continue
        seen.add(row_key)
        out.append(row)
    return out


def load_demo_user_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in iter_demo_csv_paths("tsoc_users.csv"):
        rows.extend(user_row(r) for r in read_csv(path))
    return _dedupe_rows(rows, "user_id")


def load_demo_asset_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in iter_demo_csv_paths("tsoc_assets.csv"):
        rows.extend(asset_row(r) for r in read_csv(path))
    return _dedupe_rows(rows, "asset_id")


def load_demo_relationship_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in iter_demo_csv_paths("tsoc_relationships.csv"):
        rows.extend(relationship_row(r) for r in read_csv(path))
    return _dedupe_rows(rows, "relationship_id")


def user_row(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "user_id": row["user_id"],
        "display_name": row.get("display_name") or None,
        "email": row.get("email") or None,
        "department": row.get("department") or None,
        "risk_score": int(row.get("risk_score") or 0),
        "description": row.get("description") or None,
    }


def asset_row(row: Dict[str, str]) -> Dict[str, Any]:
    crit = (row.get("criticality") or "medium").strip().lower()
    if crit not in ("low", "medium", "high", "critical"):
        crit = "medium"
    return {
        "asset_id": row["asset_id"],
        "asset_type": row.get("asset_type") or "server",
        "hostname": row.get("hostname") or None,
        "fqdn": row.get("fqdn") or None,
        "ip": row.get("ip") or None,
        "owner": row.get("owner") or None,
        "criticality": crit,
        "risk_score": int(row.get("risk_score") or 0),
        "description": row.get("description") or None,
    }


def relationship_row(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "relationship_id": row["relationship_id"],
        "user_id": row["user_id"],
        "asset_id": row["asset_id"],
        "description": row.get("description") or None,
    }


async def tables_empty(settings: Settings) -> bool:
    pool = await ensure_pool(settings)
    async with pool.acquire() as conn:
        n_users = await conn.fetchval("SELECT COUNT(*) FROM tsoc_users")
        n_assets = await conn.fetchval("SELECT COUNT(*) FROM tsoc_assets")
        n_rels = await conn.fetchval("SELECT COUNT(*) FROM tsoc_relationships")
    return not (n_users or n_assets or n_rels)


async def ensure_default_relationships(settings: Settings) -> int:
    """Create inferred relationships when inventory exists but links table is empty."""
    pool = await ensure_pool(settings)
    async with pool.acquire() as conn:
        n_rels = await conn.fetchval("SELECT COUNT(*) FROM tsoc_relationships")
        if n_rels:
            return 0
        n_users = await conn.fetchval("SELECT COUNT(*) FROM tsoc_users")
        n_assets = await conn.fetchval("SELECT COUNT(*) FROM tsoc_assets")
        if not n_users or not n_assets:
            return 0

    from services.inventory.assets import list_assets
    from services.inventory.converters import asset_record_to_dict, user_record_to_dict
    from services.inventory.exceptions import InventoryConflictError
    from services.inventory.relationships import create_relationship
    from services.inventory.users import list_users

    users = [user_record_to_dict(u) for u in await list_users(settings)]
    assets = [asset_record_to_dict(a) for a in await list_assets(settings)]
    created = 0
    for rel in build_default_relationships(users, assets):
        try:
            await create_relationship(settings, RelationshipCreate(**rel))
            created += 1
        except InventoryConflictError:
            pass
    if created:
        logger.info("inventory ensure_default_relationships created=%d", created)
    return created


async def seed_inventory_from_csv_if_empty(settings: Settings) -> None:
    if not await tables_empty(settings):
        return

    user_rows = load_demo_user_rows()
    asset_rows = load_demo_asset_rows()
    if not user_rows or not asset_rows:
        logger.warning("inventory_seed skipped: no demo CSV rows under %s", DEMO_DATA_DIR)
        return

    from services.inventory.assets import create_asset
    from services.inventory.relationships import create_relationship
    from services.inventory.users import create_user

    explicit_rels = load_demo_relationship_rows()
    merged_rels = merge_relationship_lists(
        explicit_rels,
        build_default_relationships(user_rows, asset_rows),
    )

    for row in user_rows:
        await create_user(settings, UserCreate(**row))
    for row in asset_rows:
        await create_asset(settings, AssetCreate(**row))
    for rel in merged_rels:
        await create_relationship(settings, RelationshipCreate(**rel))
    logger.info(
        "inventory_seed loaded demo CSV users=%d assets=%d relationships=%d",
        len(user_rows),
        len(asset_rows),
        len(merged_rels),
    )
