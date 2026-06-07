"""Default relationship inference from inventory rows."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.inventory.csv_seed import ensure_default_relationships
from services.inventory.default_relationships import (
    build_default_relationships,
    merge_relationship_lists,
)


def _demo_users():
    return [
        {
            "user_id": "jdoe",
            "display_name": "Jane Doe",
            "department": "IT",
            "risk_score": 3,
        },
        {
            "user_id": "asmith",
            "display_name": "Alice Smith",
            "department": "Finance",
            "risk_score": 2,
        },
    ]


def _demo_assets():
    return [
        {
            "asset_id": "srv-web-01",
            "owner": "ops",
            "hostname": "web-prod-01",
            "description": "Web tier",
        },
        {
            "asset_id": "srv-db-01",
            "owner": "dba",
            "hostname": "db-prod-01",
            "description": "Database",
        },
        {
            "asset_id": "asset-dup-a",
            "owner": "ops",
            "hostname": "dup-a",
        },
    ]


def test_build_default_links_owner_user_id():
    users = [{"user_id": "jdoe", "department": "IT"}]
    assets = [{"asset_id": "srv-1", "owner": "jdoe"}]
    rels = build_default_relationships(users, assets)
    assert len(rels) == 1
    assert rels[0]["user_id"] == "jdoe"
    assert rels[0]["asset_id"] == "srv-1"
    assert rels[0]["relationship_id"] == "rel-jdoe-srv-1"


def test_build_default_links_owner_team_to_department():
    rels = build_default_relationships(_demo_users(), _demo_assets())
    pairs = {(r["user_id"], r["asset_id"]) for r in rels}
    assert ("jdoe", "srv-web-01") in pairs
    assert ("asmith", "srv-db-01") in pairs
    assert ("jdoe", "asset-dup-a") in pairs


def test_build_default_skips_unknown_owner():
    users = [{"user_id": "u1", "department": "IT"}]
    assets = [{"asset_id": "a1", "owner": "unknown-team"}]
    assert build_default_relationships(users, assets) == []


def test_build_default_one_relationship_per_pair():
    rels = build_default_relationships(_demo_users(), _demo_assets())
    pairs = [(r["user_id"], r["asset_id"]) for r in rels]
    assert len(pairs) == len(set(pairs))


def test_merge_explicit_overrides_default_description():
    defaults = build_default_relationships(_demo_users(), [_demo_assets()[0]])
    explicit = [
        {
            "relationship_id": "rel-custom",
            "user_id": "jdoe",
            "asset_id": "srv-web-01",
            "description": "Manual override",
        }
    ]
    merged = merge_relationship_lists(explicit, defaults)
    assert len(merged) == 1
    assert merged[0]["description"] == "Manual override"
    assert merged[0]["relationship_id"] == "rel-custom"


def test_merge_combines_disjoint_pairs():
    defaults = build_default_relationships(_demo_users(), _demo_assets())
    explicit = [
        {
            "relationship_id": "rel-extra",
            "user_id": "asmith",
            "asset_id": "extra-asset",
            "description": "Extra",
        }
    ]
    merged = merge_relationship_lists(explicit, defaults)
    assert len(merged) == len(defaults) + 1


def _mock_pool(fetchval_results: list[int]) -> MagicMock:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=fetchval_results)

    class _AcquireCtx:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *_args):
            return None

    pool = MagicMock()
    pool.acquire.return_value = _AcquireCtx()
    return pool


@pytest.mark.asyncio
async def test_ensure_default_relationships_skips_when_links_exist():
    with patch("services.inventory.csv_seed.ensure_pool", new_callable=AsyncMock) as pool_m:
        pool_m.return_value = _mock_pool([2, 2, 2])
        n = await ensure_default_relationships(AsyncMock())
    assert n == 0


@pytest.mark.asyncio
async def test_ensure_default_relationships_creates_from_inventory():
    with patch("services.inventory.csv_seed.ensure_pool", new_callable=AsyncMock) as pool_m:
        pool_m.return_value = _mock_pool([0, 2, 2])
        with patch("services.inventory.users.list_users", new_callable=AsyncMock) as lu:
            with patch("services.inventory.assets.list_assets", new_callable=AsyncMock) as la:
                with patch(
                    "services.inventory.relationships.create_relationship",
                    new_callable=AsyncMock,
                ) as cr:
                    from models.inventory import AssetRecord, UserRecord

                    lu.return_value = [
                        UserRecord(user_id="jdoe", department="IT", risk_score=1),
                    ]
                    la.return_value = [
                        AssetRecord(
                            asset_id="srv-web-01",
                            asset_type="server",
                            owner="ops",
                            criticality="high",
                            risk_score=1,
                        ),
                    ]
                    cr.return_value = None
                    n = await ensure_default_relationships(AsyncMock())
    assert n == 1
    cr.assert_awaited_once()


def test_demo_csv_rows_produce_expected_defaults():
    from services.inventory.csv_seed import asset_row, read_csv, user_row
    from services.inventory.constants import DEMO_DATA_DIR

    users = [user_row(r) for r in read_csv(DEMO_DATA_DIR / "tsoc_users.csv")]
    assets = [asset_row(r) for r in read_csv(DEMO_DATA_DIR / "tsoc_assets.csv")]
    rels = build_default_relationships(users, assets)
    pairs = {(r["user_id"], r["asset_id"]) for r in rels}
    assert ("jdoe", "srv-web-01") in pairs
    assert ("asmith", "srv-db-01") in pairs
    assert len(pairs) >= 4  # includes duplicate-IP demo assets for ops/IT


def test_load_demo_csv_merges_all_scenario_packs():
    from services.inventory.csv_seed import (
        load_demo_asset_rows,
        load_demo_relationship_rows,
        load_demo_user_rows,
    )

    users = load_demo_user_rows()
    assets = load_demo_asset_rows()
    explicit = load_demo_relationship_rows()
    assert len(users) >= 7
    assert len(assets) >= 7
    assert len(explicit) >= 8
    user_ids = {u["user_id"] for u in users}
    assert "jdoe" in user_ids
    assert "leonard" in user_ids
    assert "WAYNECORPINC\\bwayne" in user_ids
    assert "platform-ops" in user_ids
