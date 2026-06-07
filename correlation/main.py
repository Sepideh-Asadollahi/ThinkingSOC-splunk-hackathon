from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from graph_api.analysis_router import router as analysis_router
from graph_api.explorer_router import router as explorer_router
from graph_api.findings_router import router as findings_router
from graph_api.internal_router import router as internal_router
from config import get_settings
from graph_core.neo4j_driver import close_driver, verify_connectivity as neo4j_ok
from graph_core.postgres_pool import close_pool, init_pool, verify_connectivity as pg_ok

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    await init_pool(settings)
    yield
    await close_pool()
    await close_driver()


app = FastAPI(
    title="Correlation",
    description="ThinkingSOC Graph Correlation demo API",
    version="0.1.0",
    lifespan=lifespan,
)

graph_router = APIRouter(prefix="/api/v1/graph")
graph_router.include_router(findings_router)
graph_router.include_router(analysis_router)
graph_router.include_router(explorer_router)
graph_router.include_router(internal_router)


@graph_router.get("/health")
async def graph_health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "neo4j": await neo4j_ok(settings),
        "postgres": await pg_ok(settings),
    }


app.include_router(graph_router)


@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "Correlation",
        "neo4j": await neo4j_ok(settings),
        "postgres": await pg_ok(settings),
    }
