#!/usr/bin/env bash
# Reload bundled moment demo into PostgreSQL (fix empty UI after install).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND="${REPO_ROOT}/backend"
VENV_PY="${BACKEND}/.venv/bin/python"
MANIFEST="${BACKEND}/data/demo/postgres_snapshot/manifest.json"

if [[ ! -x "$VENV_PY" ]]; then
    echo "[ERROR] Missing ${VENV_PY} — run install.sh or setup.py first." >&2
    exit 1
fi
if [[ ! -f "$MANIFEST" ]]; then
    echo "[ERROR] Missing demo snapshot: ${MANIFEST}" >&2
    exit 1
fi

if ! docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
    echo "[ERROR] tsoc-postgres is not ready. Start: cd ${BACKEND} && docker compose up -d" >&2
    exit 1
fi

echo "[INFO] Reloading moment demo snapshot into PostgreSQL …"
cd "$BACKEND"
"$VENV_PY" - <<'PY'
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(".env", override=True)
from config import get_settings
from services.demo.postgres_snapshot import apply_postgres_demo_bundle

async def main() -> None:
    import services.splunk_json_store.pg as pg_mod
    pg_mod._PG_POOL = None
    ok = await apply_postgres_demo_bundle(get_settings(), allow_reseed=True)
    if not ok:
        raise SystemExit("apply_postgres_demo_bundle failed")
    print("Demo snapshot applied.")

asyncio.run(main())
PY

echo "[INFO] Counts:"
docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc \
    "SELECT 'users='||COUNT(*)::text FROM tsoc_users
     UNION ALL SELECT 'records='||COUNT(*)::text FROM tsoc_records
     UNION ALL SELECT 'correlation_findings='||COUNT(*)::text FROM graph_findings;"

if [[ -x "${REPO_ROOT}/scripts/seed-correlation-demo.sh" ]]; then
    echo "[INFO] Ensuring Neo4j correlation graph matches reloaded Postgres demo …"
    bash "${REPO_ROOT}/scripts/seed-correlation-demo.sh" || echo "[WARN] Correlation seed failed — backend will retry on startup"
fi

restart_services() {
    if systemctl is-active --quiet tsoc-backend 2>/dev/null; then
        echo "[INFO] Restarting tsoc-backend and tsoc-frontend (systemd) …"
        systemctl restart tsoc-backend tsoc-frontend
        for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
            if curl -sf --noproxy '*' http://127.0.0.1:9876/health &>/dev/null; then
                echo "[OK] Backend healthy after restart"
                return 0
            fi
            sleep 5
        done
        echo "[WARN] Backend /health not ready yet (embedding may still load)"
    elif [[ -f "${REPO_ROOT}/logs/backend.pid" ]]; then
        echo "[INFO] Restarting background services …"
        sudo bash "${REPO_ROOT}/scripts/start-tsoc-services.sh" || true
    fi
}

restart_services
