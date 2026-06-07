#!/usr/bin/env python3
"""Build enriched webhook payloads for ATTACKS demo (inventory + derived graph correlation)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parents[2]
_ATTACKS_DIR = Path(__file__).resolve().parents[3] / "scripts" / "samples" / "ATTACKS"
_DEMO_DIR = _BACKEND / "data" / "demo" / "attacks_t8372"
_ENRICHED_DIR = _DEMO_DIR / "enriched_webhooks"

if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from config import get_settings
from models.handoff import normalize_splunk_ingest_payload
from models.inventory import AssetCreate, AssetUpdate, RelationshipCreate, UserCreate, UserUpdate
from services.inventory.assets import create_asset, list_assets, update_asset
from services.alert.enrichment_resolver import enrich_from_inventory
from services.alert.graph_correlation import ensure_graph_correlation_on_payload, normalize_row_data
from services.inventory.converters import asset_record_to_dict, user_record_to_dict
from services.inventory.csv_seed import asset_row, read_csv, relationship_row, user_row
from services.inventory.exceptions import InventoryConflictError
from services.inventory.relationships import create_relationship, list_relationships
from services.inventory.users import create_user, list_users, update_user

_ATTACKS_ALLOWED_TOP_LEVEL = frozenset(
    {"sid", "search_name", "app", "owner", "server_uri", "results_link", "orig_sid", "result"}
)


def list_attack_files() -> list[Path]:
    return sorted(_ATTACKS_DIR.glob("attack_step_*.json"))


def assert_attacks_file_is_splunk_only(path: Path, payload: dict[str, Any]) -> None:
    extra = set(payload.keys()) - _ATTACKS_ALLOWED_TOP_LEVEL
    if extra:
        raise SystemExit(
            f"{path.name}: ATTACKS must be Splunk webhook only; remove {sorted(extra)} "
            f"(run enrich_attacks_correlation.py to build enriched_webhooks/)"
        )
    if not payload.get("result"):
        raise SystemExit(f"{path.name}: missing result")


def _relationship_ids_for_pair(
    user_id: str | None,
    asset_id: str | None,
    relationships: list[dict[str, Any]],
) -> list[str]:
    if not user_id or not asset_id:
        return []
    uid = str(user_id).strip()
    aid = str(asset_id).strip()
    out: list[str] = []
    for rel in relationships:
        if str(rel.get("user_id") or "").strip() == uid and str(rel.get("asset_id") or "").strip() == aid:
            rid = str(rel.get("relationship_id") or "").strip()
            if rid:
                out.append(rid)
    return out


async def enrich_attack_payload(
    raw: dict[str, Any],
    *,
    users: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    settings,
) -> dict[str, Any]:
    handoff = normalize_splunk_ingest_payload(raw)
    row = dict(handoff.results[0]) if handoff.results else {}
    normalized = normalize_row_data(row)
    enrichment = enrich_from_inventory(normalized, users, assets, relationships)
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

    out: dict[str, Any] = {
        "sid": raw.get("sid"),
        "search_name": handoff.search_name,
        "app": raw.get("app") or "search",
        "owner": raw.get("owner") or "admin",
        "result": dict(row),
        "normalized": normalized,
        "enrichment": enrichment_dump,
    }
    if raw.get("server_uri"):
        out["server_uri"] = raw["server_uri"]
    if raw.get("results_link"):
        out["results_link"] = raw["results_link"]
    if raw.get("orig_sid"):
        out["orig_sid"] = raw["orig_sid"]

    return await ensure_graph_correlation_on_payload(out, settings)


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
    settings = get_settings()
    user_rows = [user_row(r) for r in read_csv(_DEMO_DIR / "tsoc_users.csv")]
    asset_rows = [asset_row(r) for r in read_csv(_DEMO_DIR / "tsoc_assets.csv")]
    rel_rows = [relationship_row(r) for r in read_csv(_DEMO_DIR / "tsoc_relationships.csv")]
    if dry_run:
        print("dry-run inventory:", len(user_rows), "users,", len(asset_rows), "assets,", len(rel_rows), "rels")
        return
    for row in user_rows:
        await _upsert_user(settings, row)
    for row in asset_rows:
        await _upsert_asset(settings, row)
    for rel in rel_rows:
        try:
            await create_relationship(settings, RelationshipCreate(**rel))
        except InventoryConflictError:
            pass
    print("inventory seeded from", _DEMO_DIR)


async def enrich_attack_files(
    *,
    write_enriched: bool,
    verify: bool,
) -> list[dict[str, Any]]:
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
    enriched_all: list[dict[str, Any]] = []

    if write_enriched:
        _ENRICHED_DIR.mkdir(parents=True, exist_ok=True)

    for path in list_attack_files():
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert_attacks_file_is_splunk_only(path, raw)
        enriched = await enrich_attack_payload(
            raw,
            users=users,
            assets=assets,
            relationships=rels,
            settings=settings,
        )
        enriched_all.append(enriched)

        if write_enriched:
            out_path = _ENRICHED_DIR / path.name
            out_path.write_text(json.dumps(enriched, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print("wrote enriched →", out_path.relative_to(_BACKEND.parent))

        if verify:
            e = enriched["enrichment"]
            if not e.get("resolved_asset_id"):
                raise SystemExit(f"{path.name}: missing resolved_asset_id — run --seed-inventory first")
            print(
                f"  {path.name}: alert={enriched['correlation']['alert_row_id']} "
                f"asset={e['resolved_asset_id']} user={e.get('resolved_user_id')} "
                f"entities={enriched['correlation']['entity_identifiers']}"
            )
    return enriched_all


async def seed_neo4j_from_attacks(enriched: list[dict[str, Any]]) -> None:
    """Upsert alerts + entities from webhook fields (incidents/CAUSED come from Attack Discovery)."""
    corr_dir = str(_BACKEND.parent / "correlation")
    if corr_dir not in sys.path:
        sys.path.insert(0, corr_dir)
    from graph_core.neo4j_driver import close_driver
    from graph_crud.alert_upsert import upsert_alert_from_webhook

    for payload in enriched:
        await upsert_alert_from_webhook(payload)
    await close_driver()
    print(f"neo4j: upserted {len(enriched)} alerts (RELATED_TO from alert fields only)")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-inventory", action="store_true", help="Upsert demo inventory into Postgres")
    parser.add_argument(
        "--seed-neo4j",
        action="store_true",
        help="Upsert ATTACKS alerts into Neo4j from derived entities (no Cypher seed)",
    )
    parser.add_argument("--dry-run", action="store_true", help="With --seed-inventory, print counts only")
    parser.add_argument(
        "--write-enriched",
        action="store_true",
        help="Write full webhook+enrichment payloads to data/demo/attacks_t8372/enriched_webhooks/",
    )
    parser.add_argument("--verify", action="store_true", help="Print enrichment summary per step")
    args = parser.parse_args()

    if args.seed_inventory:
        await seed_inventory(dry_run=args.dry_run)
    if args.dry_run and not args.seed_neo4j:
        return

    enriched = await enrich_attack_files(
        write_enriched=args.write_enriched,
        verify=args.verify or args.write_enriched,
    )
    if args.seed_neo4j:
        await seed_neo4j_from_attacks(enriched)


if __name__ == "__main__":
    asyncio.run(main())
