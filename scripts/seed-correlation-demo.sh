#!/usr/bin/env bash
# Idempotent correlation demo baseline (Postgres graph_findings + Neo4j Operation Shadow Login).
# Called automatically by clear-services-data, restore-demo-db, install, and backend health/discovery.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CORRELATION_DIR="${REPO_ROOT}/correlation"
VENV_PY="${REPO_ROOT}/backend/.venv/bin/python"

log() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*" >&2; }

if [[ ! -x "$VENV_PY" ]]; then
    echo "[ERROR] Missing backend venv: ${VENV_PY}" >&2
    exit 1
fi

if ! docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
    echo "[ERROR] tsoc-postgres not ready" >&2
    exit 1
fi

if ! docker ps --filter "name=^tsoc-neo4j$" --filter "status=running" -q 2>/dev/null | grep -q .; then
    warn "tsoc-neo4j not running — Postgres seed only; Neo4j will load on backend startup"
fi

log "Ensuring correlation demo baseline (graph_findings + Neo4j alerts if missing) …"
cd "$CORRELATION_DIR"
"$VENV_PY" - <<'PY'
import asyncio


async def main() -> None:
    from graph_crud.schema import prune_correlation_findings_to_canonical, seed_demo_data_if_empty
    from graph_core.neo4j_driver import close_driver, run_read_query
    from graph_core.postgres_pool import close_pool, get_pool

    try:
        await seed_demo_data_if_empty()
        pruned = await prune_correlation_findings_to_canonical()
        pool = get_pool()
        async with pool.acquire() as conn:
            findings = int(await conn.fetchval("SELECT COUNT(*) FROM graph_findings") or 0)
        rows = await run_read_query("MATCH (a:Alert) RETURN count(a) AS cnt")
        alerts = int((rows[0] or {}).get("cnt") or 0)
        print(f"correlation baseline: graph_findings={findings} neo4j_alerts={alerts} pruned={pruned}")
        if alerts == 0:
            raise SystemExit("Neo4j still has no Alert nodes after seed")
    finally:
        await close_pool()
        await close_driver()


asyncio.run(main())
PY

log "Correlation demo baseline ready."
