"""Demo seed: full PostgreSQL JSON snapshot (primary) or CSV fallback."""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Dict

from setup_tool.log import LOG
from setup_tool.paths import BACKEND_DIR, DEFAULT_POSTGRES_DSN, DEMO_DATA_DIR, ENV_FILE
from setup_tool.retry_util import retry_async, step_attempts


async def _connect_postgres(dsn: str):
    import asyncpg

    return await asyncpg.connect(dsn=dsn, timeout=30)


def _prepare_backend_for_seed(dsn: str) -> None:
    sys.path.insert(0, str(BACKEND_DIR))
    os.chdir(BACKEND_DIR)
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE, override=True)
    os.environ["TSOC_POSTGRES_DSN"] = dsn
    import services.splunk_json_store.pg as pg_mod

    pg_mod._PG_POOL = None


async def _verify_demo_counts(dsn: str) -> bool:
    conn = await retry_async("postgres connect", lambda: _connect_postgres(dsn))
    try:
        users = await conn.fetchval("SELECT COUNT(*)::int FROM tsoc_users")
        assets = await conn.fetchval("SELECT COUNT(*)::int FROM tsoc_assets")
        rels = await conn.fetchval("SELECT COUNT(*)::int FROM tsoc_relationships")
        records = await conn.fetchval("SELECT COUNT(*)::int FROM tsoc_records")
        identity_rules = 0
        if await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'tsoc_identity_rules'
            )
            """
        ):
            identity_rules = await conn.fetchval(
                "SELECT COUNT(*)::int FROM tsoc_identity_rules"
            )
        if not users:
            LOG.error("[SEED] No users in database after demo load")
            return False
        LOG.info(
            "[SEED] OK — users=%s assets=%s relationships=%s identity_rules=%s records=%s",
            users,
            assets,
            rels,
            identity_rules,
            records,
        )
        return True
    finally:
        await conn.close()


async def _seed_from_snapshot(dsn: str) -> bool:
    snapshot_manifest = DEMO_DATA_DIR / "postgres_snapshot" / "manifest.json"
    LOG.info("[SEED] Loading full demo snapshot from %s …", snapshot_manifest)
    _prepare_backend_for_seed(dsn)

    from config import get_settings
    from services.demo.postgres_snapshot import apply_postgres_demo_bundle

    if not await apply_postgres_demo_bundle(get_settings(), allow_reseed=True):
        LOG.error("[SEED] Failed to apply postgres_snapshot bundle")
        return False
    return await _verify_demo_counts(dsn)


async def _seed_from_csv(dsn: str) -> bool:
    LOG.info("[SEED] Loading CSV demo inventory from %s …", DEMO_DATA_DIR)
    _prepare_backend_for_seed(dsn)

    from config import get_settings
    from services.splunk_json_store import init_store

    await init_store(get_settings())
    return await _verify_demo_counts(dsn)


async def seed_inventory_if_empty(dsn: str) -> bool:
    LOG.info("[SEED] Connecting … (up to %s attempts)", step_attempts())

    if not DEMO_DATA_DIR.is_dir():
        LOG.error("[SEED] Missing demo data: %s", DEMO_DATA_DIR)
        return False

    snapshot_manifest = DEMO_DATA_DIR / "postgres_snapshot" / "manifest.json"
    if snapshot_manifest.is_file():
        return await _seed_from_snapshot(dsn)

    conn = await retry_async("postgres connect", lambda: _connect_postgres(dsn))
    try:
        count = await conn.fetchval("SELECT COUNT(*)::int FROM tsoc_users")
        if count and int(count) > 0:
            LOG.info("[SEED] Inventory has %s user(s) — skip (no snapshot manifest)", count)
            return True
    finally:
        await conn.close()

    LOG.info("[SEED] No postgres_snapshot manifest — trying CSV fallback")
    return await _seed_from_csv(dsn)


def step_seed(env: Dict[str, str], seed: bool) -> bool:
    if not seed:
        LOG.info("[SEED] Skipped (--no-seed)")
        return True
    dsn = (env.get("TSOC_POSTGRES_DSN") or DEFAULT_POSTGRES_DSN).strip()
    if not dsn:
        LOG.error("[SEED] No DSN")
        return False
    try:
        return asyncio.run(seed_inventory_if_empty(dsn))
    except Exception as e:
        import logging

        LOG.error("[SEED] %s", e, exc_info=LOG.isEnabledFor(logging.DEBUG))
        return False
