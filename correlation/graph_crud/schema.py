from __future__ import annotations

import logging
from pathlib import Path

from correlation_config import Settings, get_settings
from graph_core.postgres_pool import execute_sql_file, get_pool, init_pool

logger = logging.getLogger(__name__)

_SEED_DIR = Path(__file__).resolve().parent.parent / "seed"

# Hackathon demo: single canonical correlation finding (see postgres_demo_findings.sql).
CANONICAL_CORRELATION_FINDING_ID = "7fda487b-c5fe-4b88-b153-0958d74e4aec"
CANONICAL_CORRELATION_DISPLAY_ID = "GF-0007"


async def ensure_graph_schema(settings: Settings | None = None) -> None:
    s = settings or get_settings()
    await execute_sql_file(str(_SEED_DIR / "01_graph_findings.sql"), settings=s)


async def _neo4j_alert_count() -> int:
    from graph_core.neo4j_driver import run_read_query

    rows = await run_read_query("MATCH (a:Alert) RETURN count(a) AS cnt")
    return int((rows[0] or {}).get("cnt") or 0)


async def prune_correlation_findings_to_canonical(settings: Settings | None = None) -> int:
    """Remove every graph_findings row except the canonical GF-0007 demo finding."""
    s = settings or get_settings()
    if not s.tsoc_correlation_auto_seed:
        return 0

    await init_pool(s)
    pool = get_pool()
    canonical_id = CANONICAL_CORRELATION_FINDING_ID
    rag_doc_id = f"corr-finding:{canonical_id}"

    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM graph_findings WHERE id = $1::uuid",
            canonical_id,
        )
        if not exists:
            return 0

        result = await conn.execute(
            "DELETE FROM graph_findings WHERE id <> $1::uuid",
            canonical_id,
        )
        await conn.execute(
            """
            UPDATE graph_findings
            SET display_id = $2
            WHERE id = $1::uuid AND display_id IS DISTINCT FROM $2
            """,
            canonical_id,
            CANONICAL_CORRELATION_DISPLAY_ID,
        )
        await conn.execute(
            """
            DELETE FROM tsoc_rag_documents
            WHERE doc_type = 'correlation_finding' AND doc_id <> $1
            """,
            rag_doc_id,
        )

    deleted = 0
    if result and result.startswith("DELETE "):
        try:
            deleted = int(result.split()[-1])
        except ValueError:
            deleted = 0
    if deleted:
        logger.info(
            "correlation: pruned %d extra finding(s); kept %s",
            deleted,
            CANONICAL_CORRELATION_DISPLAY_ID,
        )
    return deleted


async def seed_demo_data_if_empty(settings: Settings | None = None) -> None:
    """Load Postgres + Neo4j demo campaign when either store lacks demo data."""
    s = settings or get_settings()
    await init_pool(s)
    pool = get_pool()
    async with pool.acquire() as conn:
        findings_count = int(await conn.fetchval("SELECT COUNT(*) FROM graph_findings") or 0)

    alert_count = await _neo4j_alert_count()
    if findings_count > 0 and alert_count > 0:
        return

    from seed.seed import seed_neo4j, seed_postgres

    if findings_count == 0:
        logger.info("correlation: empty graph_findings — loading Postgres demo seed")
        await seed_postgres()
    if alert_count == 0:
        logger.info("correlation: empty Neo4j alerts — loading Operation Shadow Login seed")
        await seed_neo4j()

    await prune_correlation_findings_to_canonical(s)
