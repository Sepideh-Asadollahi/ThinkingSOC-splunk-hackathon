"""Mount graph correlation (Neo4j) on the unified hackathon backend."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, FastAPI

logger = logging.getLogger(__name__)

_CORRELATION_DIR = Path(__file__).resolve().parent.parent.parent / "correlation"


def _ensure_correlation_path() -> None:
    path = str(_CORRELATION_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)


async def correlation_startup() -> None:
    from config import get_settings

    settings = get_settings()
    if not settings.tsoc_correlation_enabled:
        logger.info("correlation disabled (TSOC_CORRELATION_ENABLED=false)")
        return
    if not settings.tsoc_postgres_dsn:
        logger.warning("correlation skipped: TSOC_POSTGRES_DSN not set")
        return
    _ensure_correlation_path()
    from graph_core.neo4j_driver import get_driver
    from graph_core.postgres_pool import init_pool

    await init_pool(settings)
    get_driver(settings)
    from graph_crud.schema import (
        ensure_graph_schema,
        prune_correlation_findings_to_canonical,
        seed_demo_data_if_empty,
    )

    await ensure_graph_schema(settings)
    if settings.tsoc_correlation_auto_seed:
        await seed_demo_data_if_empty(settings)
        await prune_correlation_findings_to_canonical(settings)
    logger.info("correlation graph service ready (Neo4j + Postgres)")


async def upsert_webhook_alert_to_graph(payload: dict) -> None:
    """Upsert Alert + entities in Neo4j from webhook fields (no hardcoded Cypher seed)."""
    from config import get_settings

    settings = get_settings()
    if not settings.tsoc_correlation_enabled:
        return
    _ensure_correlation_path()
    try:
        from graph_crud.alert_upsert import upsert_alert_from_webhook
        from services.alert.graph_correlation import ensure_graph_correlation_on_payload

        graph_payload = await ensure_graph_correlation_on_payload(payload, settings)
        await upsert_alert_from_webhook(graph_payload)
    except Exception as exc:
        logger.debug("correlation graph upsert skipped: %s", exc)


async def correlation_shutdown() -> None:
    _ensure_correlation_path()
    try:
        from graph_core.neo4j_driver import reset_driver
        from graph_core.postgres_pool import reset_pool

        await reset_pool()
        await reset_driver()
    except Exception as exc:
        logger.debug("correlation shutdown: %s", exc)


def register_correlation_routes(app: FastAPI) -> None:
    from config import get_settings

    settings = get_settings()
    if not settings.tsoc_correlation_enabled:
        return

    _ensure_correlation_path()
    from graph_api.analysis_router import router as analysis_router
    from graph_api.explorer_router import router as explorer_router
    from graph_api.findings_router import router as findings_router
    from graph_api.internal_router import router as internal_router
    from correlation_config import get_settings as corr_settings
    from graph_core.neo4j_driver import verify_connectivity as neo4j_ok
    from graph_core.postgres_pool import verify_connectivity as pg_ok

    graph_router = APIRouter(prefix="/api/v1/graph")
    graph_router.include_router(findings_router)
    graph_router.include_router(analysis_router)
    graph_router.include_router(explorer_router)
    graph_router.include_router(internal_router)

    @graph_router.get("/health")
    async def graph_health() -> dict:
        s = corr_settings()
        if settings.tsoc_correlation_auto_seed:
            try:
                from graph_crud.schema import (
                    prune_correlation_findings_to_canonical,
                    seed_demo_data_if_empty,
                )

                await seed_demo_data_if_empty(s)
                await prune_correlation_findings_to_canonical(s)
            except Exception as exc:
                logger.debug("correlation health auto-seed skipped: %s", exc)
        return {
            "status": "ok",
            "neo4j": await neo4j_ok(s),
            "postgres": await pg_ok(s),
        }

    app.include_router(graph_router)
    logger.info("Correlation API mounted at /api/v1/graph")
