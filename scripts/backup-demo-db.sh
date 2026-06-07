#!/usr/bin/env bash
# Capture a full PostgreSQL backup of the demo database into the repo.
# pg_dump has NO row limits — every table and every row is included.
#
# Output: backend/data/demo/postgres_dump/tsoc_demo.sql
# Transfer to a new server: commit + push, or scp the file and run restore-demo-db.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DUMP_DIR="${REPO_ROOT}/backend/data/demo/postgres_dump"
DUMP_FILE="${DUMP_DIR}/tsoc_demo.sql"

usage() {
    cat <<'EOF'
Usage: bash scripts/backup-demo-db.sh [--json-full]

  Default: pg_dump entire tsoc database → backend/data/demo/postgres_dump/tsoc_demo.sql
            (no row limits; this is the primary path for new servers)

  --json-full  Also refresh postgres_snapshot/ JSON with ALL rows (fallback path)

After backup on source machine:
  git add backend/data/demo/postgres_dump/tsoc_demo.sql
  git commit -m "chore: refresh demo db backup"
  git push

On destination:
  git pull
  sudo bash scripts/restore-demo-db.sh

Or copy without git:
  scp backend/data/demo/postgres_dump/tsoc_demo.sql user@newhost:/opt/.../backend/data/demo/postgres_dump/
  ssh user@newhost 'sudo bash /opt/.../scripts/restore-demo-db.sh'
EOF
}

JSON_FULL=false
for arg in "$@"; do
    case "$arg" in
        -h|--help) usage; exit 0 ;;
        --json-full) JSON_FULL=true ;;
        *) echo "[ERROR] Unknown option: $arg" >&2; usage >&2; exit 1 ;;
    esac
done

if ! docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
    echo "[ERROR] tsoc-postgres is not ready. Start: cd ${REPO_ROOT}/backend && docker compose up -d" >&2
    exit 1
fi

echo "[INFO] Current PostgreSQL contents (what will be dumped — no limits):"
docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc \
    "SELECT 'tsoc_users='||COUNT(*)::text FROM tsoc_users
     UNION ALL SELECT 'tsoc_records='||COUNT(*)::text FROM tsoc_records
     UNION ALL SELECT 'analyses(soc+obs)='||COUNT(*)::text FROM tsoc_records
       WHERE tsoc_record_type IN ('soc_analysis','observability_analysis')
     UNION ALL SELECT 'graph_findings='||COUNT(*)::text FROM graph_findings
     UNION ALL SELECT 'tsoc_rag_documents='||COUNT(*)::text FROM tsoc_rag_documents
     UNION ALL SELECT 'tsoc_chat_conversations='||COUNT(*)::text FROM tsoc_chat_conversations
     UNION ALL SELECT 'tsoc_chat_messages='||COUNT(*)::text FROM tsoc_chat_messages;" \
    2>/dev/null | grep -viE 'WARNING|NOTICE' | sed 's/^/       /'

mkdir -p "$DUMP_DIR"
echo "[INFO] Dumping FULL database (tsoc) → ${DUMP_FILE} …"
docker exec tsoc-postgres pg_dump -U tsoc -d tsoc \
    --no-owner --no-privileges --clean --if-exists > "$DUMP_FILE"

echo "[OK] Backup written ($(wc -l < "$DUMP_FILE") lines, $(du -h "$DUMP_FILE" | cut -f1))"
echo "[INFO] This file contains ALL rows currently in PostgreSQL — nothing is truncated."

if [[ "$JSON_FULL" == true ]]; then
    VENV_PY="${REPO_ROOT}/backend/.venv/bin/python"
    if [[ ! -x "$VENV_PY" ]]; then
        echo "[WARN] --json-full skipped: ${VENV_PY} not found (run install or pip install first)" >&2
    else
        echo "[INFO] Exporting full JSON snapshot (all tables, no row limits) …"
        (cd "${REPO_ROOT}/backend" && "$VENV_PY" scripts/seed/export_demo_postgres_snapshot.py --full)
    fi
fi

echo "[INFO] Commit and push so new servers get identical data:"
echo "       git add backend/data/demo/postgres_dump/tsoc_demo.sql && git commit -m 'chore: refresh demo db backup'"
