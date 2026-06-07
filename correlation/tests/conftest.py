from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

CORRELATION_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = CORRELATION_DIR.parent / "backend"

for path in (BACKEND_DIR, CORRELATION_DIR):
    s = str(path)
    if s not in sys.path:
        sys.path.insert(0, s)


def _load_backend_app():
    spec = importlib.util.spec_from_file_location("tsoc_backend_main", BACKEND_DIR / "main.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load backend/main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


@pytest_asyncio.fixture
async def client():
    from config import get_settings
    from graph_core.neo4j_driver import discard_driver, reset_driver
    from graph_core.postgres_pool import discard_pool, reset_pool
    from seed.seed import seed_neo4j, seed_postgres

    app = _load_backend_app()
    get_settings.cache_clear()
    discard_pool()
    discard_driver()

    await seed_postgres()
    await seed_neo4j()
    discard_pool()
    discard_driver()

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    await reset_pool()
    await reset_driver()
    get_settings.cache_clear()
