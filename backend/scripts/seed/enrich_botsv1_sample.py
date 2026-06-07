#!/usr/bin/env python3
"""Seed botsv1 inventory relationships and enrich scripts/samples/splunk-webhook-botsv1-osk-sysmon.json."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parents[2]
_REPO = _BACKEND.parent
_SAMPLE = _REPO / "scripts" / "samples" / "splunk-webhook-botsv1-osk-sysmon.json"
_DEMO_DIR = _BACKEND / "data" / "demo" / "botsv1_osk_sysmon"

if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from config import get_settings
from models.handoff import normalize_splunk_ingest_payload
from models.inventory import AssetCreate, AssetUpdate, RelationshipCreate, UserCreate, UserUpdate
from services.alert.enrichment_resolver import enrich_from_inventory
from services.inventory.assets import create_asset, list_assets, update_asset
from services.inventory.converters import asset_record_to_dict, user_record_to_dict
from services.inventory.csv_seed import asset_row, read_csv, relationship_row, user_row
from services.inventory.exceptions import InventoryConflictError
from services.inventory.relationships import create_relationship, list_relationships
from services.inventory.users import create_user, list_users, update_user

# Reuse relationship id attachment from ATTACKS enricher
from enrich_attacks_correlation import _relationship_ids_for_pair  # noqa: E402

_EXPECTED_ASSET = "botsv1-we8105desk"
_EXPECTED_USER = "SYSTEM"
_EXPECTED_REL = "rel-botsv1-system-desk"


async def _upsert_user(settings, row: dict) -> None:
    body = UserCreate(**row)
    try:
        await create_user(settings, body)
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


async def _upsert_asset(settings, row: dict) -> None:
    body = AssetCreate(**row)
    try:
        await create_asset(settings, body)
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


async def seed_inventory(*, dry_run: bool) -> None:
    user_rows = [user_row(r) for r in read_csv(_DEMO_DIR / "tsoc_users.csv")]
    asset_rows = [asset_row(r) for r in read_csv(_DEMO_DIR / "tsoc_assets.csv")]
    rel_rows = [relationship_row(r) for r in read_csv(_DEMO_DIR / "tsoc_relationships.csv")]
    if dry_run:
        print(f"dry-run: {len(user_rows)} users, {len(asset_rows)} assets, {len(rel_rows)} relationships")
        return
    settings = get_settings()
    for row in user_rows:
        await _upsert_user(settings, row)
    for row in asset_rows:
        await _upsert_asset(settings, row)
    for rel in rel_rows:
        try:
            await create_relationship(settings, RelationshipCreate(**rel))
        except InventoryConflictError:
            pass
    print(f"inventory seeded from {_DEMO_DIR} ({len(rel_rows)} relationships)")


def enrich_sample_payload(
    payload: dict[str, Any],
    *,
    users: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> dict[str, Any]:
    handoff = normalize_splunk_ingest_payload(payload)
    enrichment = enrich_from_inventory(handoff.normalized, users, assets, relationships)
    rel_ids = list(enrichment.matched_relationship_ids)
    for rid in _relationship_ids_for_pair(
        enrichment.resolved_user_id,
        enrichment.resolved_asset_id,
        relationships,
    ):
        if rid not in rel_ids:
            rel_ids.append(rid)
    enrichment_dump = enrichment.model_dump()
    enrichment_dump["matched_relationship_ids"] = rel_ids
    if rel_ids and "relationship" not in enrichment_dump.get("notes", "").lower():
        enrichment_dump["notes"] = (
            enrichment_dump.get("notes", "") + "; Linked via relationship(s): " + ", ".join(rel_ids)
        ).strip("; ")

    out = dict(payload)
    out["normalized"] = handoff.normalized
    out["enrichment"] = enrichment_dump
    return out


async def enrich_and_write(*, sample: Path, verify: bool) -> None:
    settings = get_settings()
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
    bots_rels = [r for r in rels if r.get("asset_id") == _EXPECTED_ASSET]
    print(f"botsv1 relationships in DB: {[r['relationship_id'] for r in bots_rels]}")

    raw = json.loads(sample.read_text(encoding="utf-8"))
    enriched = enrich_sample_payload(raw, users=users, assets=assets, relationships=rels)
    sample.write_text(json.dumps(enriched, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", sample)

    e = enriched["enrichment"]
    if verify:
        if e.get("resolved_asset_id") != _EXPECTED_ASSET:
            raise SystemExit(f"expected asset {_EXPECTED_ASSET}, got {e.get('resolved_asset_id')}")
        if e.get("resolved_user_id") != _EXPECTED_USER:
            raise SystemExit(f"expected user {_EXPECTED_USER}, got {e.get('resolved_user_id')}")
        if _EXPECTED_REL not in (e.get("matched_relationship_ids") or []):
            raise SystemExit(f"expected rel {_EXPECTED_REL} in {e.get('matched_relationship_ids')}")
        print(
            f"OK asset={e['resolved_asset_id']} user={e['resolved_user_id']} "
            f"rels={e['matched_relationship_ids']}"
        )


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-inventory", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sample", type=Path, default=_SAMPLE)
    parser.add_argument("--verify", action="store_true", default=True)
    parser.add_argument("--no-verify", action="store_false", dest="verify")
    args = parser.parse_args()

    if args.seed_inventory:
        await seed_inventory(dry_run=args.dry_run)
    if args.dry_run and not args.sample.exists():
        return
    await enrich_and_write(sample=args.sample.resolve(), verify=args.verify)


if __name__ == "__main__":
    asyncio.run(main())
