"""Ensure local Docker Postgres is up before `run.py` starts uvicorn (dev convenience)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent


def _skip_ensure() -> bool:
    return os.environ.get("TSOC_RUN_SKIP_POSTGRES", "").strip().lower() in ("1", "true", "yes")


def _configured_dsn() -> Optional[str]:
    dsn = (os.environ.get("TSOC_POSTGRES_DSN") or "").strip()
    return dsn or None


def postgres_reachable(dsn: str, *, timeout_sec: float = 3.0) -> bool:
    try:
        import asyncpg
    except ImportError:
        return False

    async def probe() -> bool:
        try:
            conn = await asyncpg.connect(dsn=dsn, timeout=timeout_sec)
            await conn.close()
            return True
        except Exception:
            return False

    return asyncio.run(probe())


def ensure_dev_postgres() -> None:
    """Start Docker Postgres when DSN is set but the server is not accepting connections."""
    if _skip_ensure():
        return
    dsn = _configured_dsn()
    if not dsn:
        return
    if postgres_reachable(dsn):
        return

    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    from setup_tool.docker import step_docker_postgres

    sys.stderr.write("PostgreSQL not reachable — starting tsoc-postgres (Docker) …\n")
    if not step_docker_postgres(start_postgres=True, skip_docker=False, dsn=dsn):
        sys.stderr.write(
            "Could not start PostgreSQL for TSOC_POSTGRES_DSN.\n"
            "  Check Docker is running: docker ps\n"
            "  Or skip auto-start: TSOC_RUN_SKIP_POSTGRES=1 python3 run.py\n"
        )
        raise SystemExit(1)
    sys.stderr.write("PostgreSQL is ready.\n")
