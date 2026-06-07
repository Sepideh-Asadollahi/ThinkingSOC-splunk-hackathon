#!/usr/bin/env python3
"""Idempotent seed: Postgres migration + demo findings + Neo4j campaign graph."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

CORRELATION_DIR = Path(__file__).resolve().parents[1]
if str(CORRELATION_DIR) not in sys.path:
    sys.path.insert(0, str(CORRELATION_DIR))

SEED_DIR = Path(__file__).resolve().parent


async def seed_postgres() -> None:
    from correlation_config import get_settings
    from graph_core.postgres_pool import execute_sql_file

    settings = get_settings()
    await execute_sql_file(str(SEED_DIR / "01_graph_findings.sql"), settings=settings)
    await execute_sql_file(str(SEED_DIR / "postgres_demo_findings.sql"), settings=settings)
    print("postgres: graph_findings migrated and demo rows seeded")


async def seed_neo4j() -> None:
    from correlation_config import get_settings
    from graph_core.neo4j_driver import get_driver

    cypher = (SEED_DIR / "neo4j_demo_campaign.cypher").read_text(encoding="utf-8")
    statements = [s.strip() for s in cypher.split(";") if s.strip()]
    driver = get_driver(get_settings())
    async with driver.session() as session:
        tx = await session.begin_transaction()
        try:
            for stmt in statements:
                await tx.run(stmt)
            await tx.commit()
        except Exception:
            await tx.rollback()
            raise
    print(f"neo4j: executed {len(statements)} statements (Operation Shadow Login)")


async def main() -> None:
    await seed_postgres()
    await seed_neo4j()
    from graph_core.neo4j_driver import close_driver
    from graph_core.postgres_pool import close_pool

    await close_pool()
    await close_driver()
    print("seed complete")


if __name__ == "__main__":
    asyncio.run(main())
