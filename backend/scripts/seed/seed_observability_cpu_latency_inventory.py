#!/usr/bin/env python3
"""Seed PostgreSQL inventory for observability CPU/latency webhook sample enrichment."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_SAMPLE = _REPO / "scripts" / "samples" / "splunk-webhook-observability-cpu-latency.json"
_DEMO_DIR = Path(__file__).resolve().parents[2] / "data" / "demo" / "observability_cpu_latency"

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import get_settings
from models.inventory import AssetCreate, AssetUpdate, RelationshipCreate, UserCreate, UserUpdate
from services.alert.enrichment_resolver import enrich_from_inventory
from services.inventory.assets import create_asset, get_asset, list_assets, update_asset
from services.inventory.converters import asset_record_to_dict, user_record_to_dict
from services.inventory.csv_seed import asset_row, read_csv, relationship_row, user_row
from services.inventory.exceptions import InventoryConflictError
from services.inventory.relationships import create_relationship, list_relationships
from services.inventory.users import create_user, get_user, list_users, update_user


def _normalized_from_sample(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    result = data.get("result")
    if not isinstance(result, dict):
        raise ValueError("sample JSON missing object 'result'")
    return {k: v for k, v in result.items() if not str(k).startswith("_")}


async def _upsert_user(settings, row: dict) -> str:
    body = UserCreate(**row)
    try:
        await create_user(settings, body)
        return "created"
    except InventoryConflictError:
        await update_user(
            settings,
            body.user_id,
            UserUpdate(
                display_name=body.display_name,
                email=body.email,
                department=body.department,
                risk_score=body.risk_score,
                description=body.description,
            ),
        )
        return "updated"


async def _upsert_asset(settings, row: dict) -> str:
    body = AssetCreate(**row)
    try:
        await create_asset(settings, body)
        return "created"
    except InventoryConflictError:
        await update_asset(
            settings,
            body.asset_id,
            AssetUpdate(
                asset_type=body.asset_type,
                hostname=body.hostname,
                fqdn=body.fqdn,
                ip=body.ip,
                owner=body.owner,
                criticality=body.criticality,
                risk_score=body.risk_score,
                description=body.description,
            ),
        )
        return "updated"


async def _seed_rows(settings, *, dry_run: bool) -> tuple[int, int, int, int, int]:
    users_path = _DEMO_DIR / "tsoc_users.csv"
    assets_path = _DEMO_DIR / "tsoc_assets.csv"
    rels_path = _DEMO_DIR / "tsoc_relationships.csv"
    user_rows = [user_row(r) for r in read_csv(users_path)]
    asset_rows = [asset_row(r) for r in read_csv(assets_path)]
    rel_rows = [relationship_row(r) for r in read_csv(rels_path)]

    created_u = updated_u = created_a = updated_a = created_r = 0
    for row in user_rows:
        if dry_run:
            created_u += 1
            continue
        if (await _upsert_user(settings, row)) == "created":
            created_u += 1
        else:
            updated_u += 1
    for row in asset_rows:
        if dry_run:
            created_a += 1
            continue
        if (await _upsert_asset(settings, row)) == "created":
            created_a += 1
        else:
            updated_a += 1
    for rel in rel_rows:
        if dry_run:
            created_r += 1
            continue
        try:
            await create_relationship(settings, RelationshipCreate(**rel))
            created_r += 1
        except InventoryConflictError:
            pass
    return created_u, updated_u, created_a, updated_a, created_r


async def _verify_enrichment(settings, normalized: dict) -> None:
    users = [user_record_to_dict(u) for u in await list_users(settings)]
    assets = [asset_record_to_dict(a) for a in await list_assets(settings)]
    rels = [
        {
            "relationship_id": r.relationship_id,
            "user_id": r.user_id,
            "asset_id": r.asset_id,
            "description": r.description,
        }
        for r in await list_relationships(settings)
    ]
    out = enrich_from_inventory(normalized, users, assets, rels)
    print("enrichment:", out.model_dump())
    if out.resolved_asset_id != "obs-web-prod-01":
        raise SystemExit("expected resolved_asset_id=obs-web-prod-01, got {0}".format(out.resolved_asset_id))


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample",
        type=Path,
        default=_DEFAULT_SAMPLE,
        help="Webhook JSON used to verify enrichment (default: observability CPU/latency sample)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print rows only; do not write DB")
    args = parser.parse_args()
    settings = get_settings()
    normalized = _normalized_from_sample(args.sample.resolve())
    print("sample host={0!r} service={1!r}".format(normalized.get("host"), normalized.get("service")))

    cu, uu, ca, ua, cr = await _seed_rows(settings, dry_run=args.dry_run)
    print(
        "users created={0} updated={1}; assets created={2} updated={3}; relationships created={4}".format(
            cu, uu, ca, ua, cr
        )
    )
    if args.dry_run:
        return
    await _verify_enrichment(settings, normalized)
    asset = await get_asset(settings, "obs-web-prod-01")
    user = await get_user(settings, "platform-ops")
    print("asset:", asset.model_dump())
    print("user:", user.model_dump())
    print("ok: enrichment matches obs-web-prod-01 on host=web-prod-01")


if __name__ == "__main__":
    asyncio.run(main())
