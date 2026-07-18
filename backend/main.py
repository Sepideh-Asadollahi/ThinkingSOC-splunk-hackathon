import asyncio
import contextlib
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import (
    admin_org,
    agents,
    analysis,
    assistant,
    dashboard,
    health,
    ingest,
    investigation,
    integrations,
    inventory,
    llm,
    mcp,
    observability,
    soc_chat,
    storage,
    triage,
)
from api.exception_handlers import register_exception_handlers
from middleware import RejectConfigQueryParamsMiddleware, RequestLoggingMiddleware
from config import get_settings
from services.correlation_integration import (
    correlation_shutdown,
    correlation_startup,
    register_correlation_routes,
)
from services.splunk_json_store import close_store, init_store


def _configure_logging() -> None:
    level_name = (os.environ.get("LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    # httpx logs every request at INFO; virustotal service logs failures with context.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        from config import get_settings
        from services.llm.full_trace_log import configure_trace_logging

        configure_trace_logging(get_settings())
    except Exception:
        pass


_configure_logging()


async def _saia_startup(settings) -> None:
    if not settings.tsoc_saia_auto_repair or not settings.tsoc_spl_use_rest_predict:
        return
    if not settings.splunk_username or not settings.splunk_password:
        return
    try:
        from splunk.saia_config_repair import ensure_saia_cloud_configs

        if await ensure_saia_cloud_configs(settings):
            logging.getLogger(__name__).info("SAIA cloud configs ready")
    except Exception as e:
        logging.getLogger(__name__).warning("SAIA startup check skipped: %s", e)


async def _rag_startup(settings) -> None:
    if not settings.tsoc_postgres_dsn:
        return
    try:
        from services.soc_rag.backfill import backfill_from_storage
        from services.soc_rag.pg_store import ensure_rag_schema
        from services.soc_rag.qdrant_store import (
            QDRANT_FIX_HINT,
            ensure_qdrant_collection,
            qdrant_enabled,
            wait_for_qdrant_ready,
        )

        await ensure_rag_schema(settings)
        if qdrant_enabled(settings):
            if not await wait_for_qdrant_ready(settings, timeout_sec=60):
                logging.getLogger(__name__).warning(
                    "qdrant not ready on %s (postgres RAG still works) — %s",
                    settings.qdrant_url,
                    QDRANT_FIX_HINT,
                )
            else:
                try:
                    from services.soc_rag.embeddings import (
                        effective_embedding_dim,
                        ensure_embedding_model,
                        resolve_embedding_model,
                    )

                    await ensure_embedding_model(settings)
                    resolved_model = resolve_embedding_model(settings.tsoc_embedding_model)
                    expected_dim = effective_embedding_dim(settings)
                    if settings.tsoc_embedding_dim != expected_dim:
                        logging.getLogger(__name__).warning(
                            "TSOC_EMBEDDING_DIM=%s ignored; %s (%s) uses dim=%s",
                            settings.tsoc_embedding_dim,
                            settings.tsoc_embedding_model,
                            resolved_model,
                            expected_dim,
                        )
                    await ensure_qdrant_collection(settings)
                except Exception as qe:
                    logging.getLogger(__name__).warning(
                        "qdrant startup skipped (postgres RAG still works): %s — %s",
                        qe,
                        QDRANT_FIX_HINT,
                    )
        if settings.tsoc_rag_backfill_on_startup and settings.tsoc_postgres_dsn:
            counts = await backfill_from_storage(settings, limit_per_type=150)
            logging.getLogger(__name__).info("rag backfill on startup: %s", counts)
    except Exception as e:
        logging.getLogger(__name__).warning("rag startup skipped: %s", e)


@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    settings = get_settings()
    await init_store(settings)
    await _saia_startup(settings)
    # Correlation Postgres/Neo4j schema + demo seed before RAG backfill (graph_findings, Alert nodes).
    await correlation_startup()

    async def _rag_background() -> None:
        try:
            await _rag_startup(settings)
        except Exception as e:
            logging.getLogger(__name__).warning("background RAG startup failed: %s", e)

    # Load embedding model / Qdrant in background so GET /health is available quickly
    # (install smoke test and systemd status checks depend on early liveness).
    rag_task = asyncio.create_task(_rag_background())

    try:
        yield
    finally:
        rag_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await rag_task
        await correlation_shutdown()
        await close_store()


app = FastAPI(
    title="ThinkingSOC Lite Splunk Hackathon Backend",
    description="Ingest from Splunk Alert Action and Splunk REST enrichment",
    version="0.4.1",
    lifespan=_app_lifespan,
)

register_exception_handlers(app)

app.add_middleware(RejectConfigQueryParamsMiddleware)
app.add_middleware(RequestLoggingMiddleware)

register_correlation_routes(app)

app.include_router(health.router)
app.include_router(health.router, prefix="/api/v1")
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(admin_org.router, prefix="/api/v1")
app.include_router(llm.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(observability.router, prefix="/api/v1")
app.include_router(assistant.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(mcp.router, prefix="/api/v1")
app.include_router(integrations.router, prefix="/api/v1")
app.include_router(storage.router, prefix="/api/v1")
app.include_router(investigation.router, prefix="/api/v1")
app.include_router(triage.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(soc_chat.router, prefix="/api/v1")
