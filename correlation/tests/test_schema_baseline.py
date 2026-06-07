from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_seed_demo_data_repairs_empty_neo4j_while_postgres_has_findings():
    """Postgres restore / partial clear can leave Neo4j empty — baseline must self-heal."""
    from graph_core.neo4j_driver import close_driver, run_write_query
    from graph_core.postgres_pool import close_pool
    from graph_crud.schema import _neo4j_alert_count, seed_demo_data_if_empty
    from seed.seed import seed_postgres

    await seed_postgres()
    await run_write_query("MATCH (n) DETACH DELETE n")

    assert await _neo4j_alert_count() == 0

    await seed_demo_data_if_empty()

    assert await _neo4j_alert_count() >= 5

    await close_pool()
    await close_driver()
