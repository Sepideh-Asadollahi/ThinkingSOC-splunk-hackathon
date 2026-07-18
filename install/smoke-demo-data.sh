#!/usr/bin/env bash
# Non-destructive smoke test for both install demo restore paths and live APIs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${TSOC_INSTALL_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
BACKEND="${INSTALL_DIR}/backend"
VENV_PYTHON="${BACKEND}/.venv/bin/python"
CONTRACT_SCRIPT="${BACKEND}/scripts/smoke_demo_contract.py"
DUMP_FILE="${BACKEND}/data/demo/postgres_dump/tsoc_demo.sql"
SNAPSHOT_DIR="${BACKEND}/data/demo/postgres_snapshot"
DB_PREFIX="tsoc_smoke_$$_$(date +%s)"
SQL_DB="${DB_PREFIX}_sql"
JSON_DB="${DB_PREFIX}_json"
CREATED_DBS=()

cleanup() {
    local db
    for db in "${CREATED_DBS[@]:-}"; do
        [[ -n "$db" ]] || continue
        docker exec tsoc-postgres psql -U tsoc -d postgres -v ON_ERROR_STOP=1 -q \
            -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${db}' AND pid <> pg_backend_pid();" \
            >/dev/null 2>&1 || true
        docker exec tsoc-postgres dropdb -U tsoc --if-exists "$db" >/dev/null 2>&1 || true
    done
}
trap cleanup EXIT INT TERM

fail() { echo "[FAIL] $*" >&2; exit 1; }
pass() { echo "[OK]   $*"; }
info() { echo "[INFO] $*"; }

[[ -x "$VENV_PYTHON" ]] || fail "Backend virtualenv missing: ${VENV_PYTHON}"
[[ -f "$CONTRACT_SCRIPT" ]] || fail "Demo contract checker missing: ${CONTRACT_SCRIPT}"
[[ -f "$DUMP_FILE" ]] || fail "SQL demo dump missing: ${DUMP_FILE}"
[[ -f "${SNAPSHOT_DIR}/manifest.json" ]] || fail "JSON demo manifest missing"
command -v docker >/dev/null 2>&1 || fail "Docker is required"
docker exec tsoc-postgres pg_isready -U tsoc -d tsoc >/dev/null 2>&1 \
    || fail "tsoc-postgres is not ready"

info "Validating committed JSON snapshot, SOC runner pipeline, previous scenarios, Runbook, Autopilot, Chat/RAG, and SPL self-repair"
PYTHONPATH="$BACKEND" "$VENV_PYTHON" "$CONTRACT_SCRIPT" --snapshot-dir "$SNAPSHOT_DIR"
pass "Committed JSON snapshot contract"

create_temp_db() {
    local db="$1"
    docker exec tsoc-postgres createdb -U tsoc "$db"
    CREATED_DBS+=("$db")
}

info "Restoring primary pg_dump into isolated database ${SQL_DB}"
create_temp_db "$SQL_DB"
docker exec -i tsoc-postgres psql -U tsoc -d "$SQL_DB" -v ON_ERROR_STOP=1 -q \
    < "$DUMP_FILE"
PYTHONPATH="$BACKEND" "$VENV_PYTHON" "$CONTRACT_SCRIPT" \
    --database-url "postgresql://tsoc:tsoc@127.0.0.1:5432/${SQL_DB}"
pass "Primary SQL dump restore and full feature contract"

info "Restoring JSON fallback into isolated database ${JSON_DB}"
create_temp_db "$JSON_DB"
(
    cd "$BACKEND"
    TSOC_POSTGRES_DSN="postgresql://tsoc:tsoc@127.0.0.1:5432/${JSON_DB}" \
    PYTHONPATH="$BACKEND" "$VENV_PYTHON" - <<'PY'
import asyncio
from pathlib import Path

from config import Settings
from services.demo.postgres_snapshot import apply_postgres_demo_bundle


async def main() -> None:
    settings = Settings(
        tsoc_postgres_dsn=__import__("os").environ["TSOC_POSTGRES_DSN"]
    )
    ok = await apply_postgres_demo_bundle(
        settings,
        demo_data_dir=Path("data/demo"),
        allow_reseed=True,
    )
    if not ok:
        raise SystemExit("JSON snapshot restore returned false")


asyncio.run(main())
PY
)
PYTHONPATH="$BACKEND" "$VENV_PYTHON" "$CONTRACT_SCRIPT" \
    --database-url "postgresql://tsoc:tsoc@127.0.0.1:5432/${JSON_DB}"
pass "JSON fallback restore and full feature contract"

info "Validating the currently installed tsoc database"
PYTHONPATH="$BACKEND" "$VENV_PYTHON" "$CONTRACT_SCRIPT" \
    --database-url "postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc"
pass "Installed database contains old and new demo scenarios"

if curl -sf --noproxy '*' --max-time 5 http://127.0.0.1:9876/health >/dev/null 2>&1; then
    token="$(sed -n 's/^TSOC_INGEST_TOKEN=//p' "${BACKEND}/.env" | head -1)"
    auth=()
    [[ -n "$token" ]] && auth=(-H "Authorization: Bearer ${token}")
    source_id="$(docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc \
        "SELECT id FROM tsoc_records WHERE tsoc_record_type='soc_analysis' AND sid='demo-runbook-source-20260716' LIMIT 1;" \
        | tr -d '[:space:]')"
    [[ "$source_id" =~ ^[0-9]+$ ]] || fail "Cannot resolve judge-tour source record id"

    tmp="$(mktemp)"
    api_get() {
        local url="$1"
        curl -sS --noproxy '*' --max-time 20 "${auth[@]}" -o "$tmp" -w '%{http_code}' "$url"
    }

    http="$(api_get "http://127.0.0.1:9876/api/v1/investigation/runbooks?search_name=Judge%20Demo%3A%20Suspicious%20OAuth%20Token%20Replay")"
    [[ "$http" == "200" ]] || fail "Runbook Library API returned HTTP ${http}"
    "$VENV_PYTHON" - "$tmp" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
item = d["groups"][0]["runbooks"][0]
assert item["draft"]["status"] == "SOURCE_VERIFIED"
assert item["latest_approval"]["decision"] == "approve"
assert item["latest_run"]["status"] == "REUSED"
PY
    pass "Live Runbook Library API"

    http="$(api_get "http://127.0.0.1:9876/api/v1/investigation/records/${source_id}/runbook/autopilot")"
    [[ "$http" == "200" ]] || fail "Autopilot API returned HTTP ${http}"
    "$VENV_PYTHON" - "$tmp" <<'PY'
import json, sys
s = json.load(open(sys.argv[1], encoding="utf-8"))["latest_session"]
assert s["status"] == "COMPLETED"
assert len(s["agents"]) == 5
assert len(s["trace"]) >= 10
assert s["human_approval_required"] is True
assert s["automatic_execution_performed"] is False
PY
    pass "Live Runbook Autopilot API"

    runner_sid='scheduler__admin__search__t8372_c2_at_1727841780.1'
    http="$(api_get "http://127.0.0.1:9876/api/v1/storage/events?sid=${runner_sid}&limit=100")"
    [[ "$http" == "200" ]] || fail "SOC runner storage API returned HTTP ${http}"
    "$VENV_PYTHON" - "$tmp" <<'PY'
import json, sys

required = {
    "soc_analysis", "soc_analysis_audit", "soc_investigation_raw_alert",
    "soc_investigation_alert_fields", "soc_investigation_defender",
    "soc_investigation_hunter", "soc_investigation_judge",
    "soc_investigation_questions", "soc_investigation_framework",
    "soc_investigation_enrichment", "soc_investigation_risk",
    "soc_investigation_threat_intel", "soc_investigation_summary",
    "soc_investigation_evidence_chain",
}
d = json.load(open(sys.argv[1], encoding="utf-8"))
rows = d["results"]
types = {row["tsoc_record_type"] for row in rows}
assert required <= types, sorted(required - types)
assert all(row["search_name"] == "PaloAlto: Outbound Connection to Known C2 (t8372)" for row in rows)
assert any(row["tsoc_record_type"] == "soc_analysis" for row in rows)
PY
    pass "Live SOC runner API serves all 14 persisted pipeline record types"

    http="$(api_get "http://127.0.0.1:9876/api/v1/soc/chat/conversations/demo-runbook-judge-tour-v1")"
    [[ "$http" == "200" ]] || fail "Chat demo API returned HTTP ${http}"
    "$VENV_PYTHON" - "$tmp" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
assert [m["role"] for m in d["messages"]] == ["user", "assistant"]
assert "Runbook Library" in d["messages"][1]["content"]
PY
    rm -f "$tmp"
    pass "Live Chat API serves the Runbook guide"

    if curl -sf --noproxy '*' --max-time 5 http://127.0.0.1:3000/login >/dev/null 2>&1; then
        frontend_env="${INSTALL_DIR}/frontend/.env.local"
        demo_user="$(sed -n 's/^TSOC_DEMO_USER=//p' "$frontend_env" | head -1)"
        demo_pass="$(sed -n 's/^TSOC_DEMO_PASSWORD=//p' "$frontend_env" | head -1)"
        demo_user="${demo_user:-admin}"
        demo_pass="${demo_pass:-123456@a}"
        cookie_jar="$(mktemp)"
        login_http="$(curl -sS --noproxy '*' --max-time 15 -c "$cookie_jar" \
            -o /dev/null -w '%{http_code}' -X POST \
            http://127.0.0.1:3000/api/auth/login \
            -H 'Content-Type: application/json' \
            --data "{\"username\":\"${demo_user}\",\"password\":\"${demo_pass}\"}")"
        [[ "$login_http" == "200" ]] || fail "Frontend demo login returned HTTP ${login_http}"
        page_http="$(curl -sS --noproxy '*' --max-time 20 -b "$cookie_jar" \
            -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/runbooks/library)"
        [[ "$page_http" == "200" ]] || fail "Runbook Library page returned HTTP ${page_http}"
        tmp="$(mktemp)"
        proxy_http="$(curl -sS --noproxy '*' --max-time 20 -b "$cookie_jar" \
            -o "$tmp" -w '%{http_code}' \
            'http://127.0.0.1:3000/api/backend/investigation/runbooks?search_name=Judge%20Demo%3A%20Suspicious%20OAuth%20Token%20Replay')"
        [[ "$proxy_http" == "200" ]] || fail "Frontend Runbook API proxy returned HTTP ${proxy_http}"
        "$VENV_PYTHON" - "$tmp" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
assert d["groups"][0]["runbooks"][0]["draft"]["status"] == "SOURCE_VERIFIED"
PY
        proxy_http="$(curl -sS --noproxy '*' --max-time 20 -b "$cookie_jar" \
            -o "$tmp" -w '%{http_code}' \
            'http://127.0.0.1:3000/api/backend/storage/events?sid=scheduler__admin__search__t8372_c2_at_1727841780.1&limit=100')"
        [[ "$proxy_http" == "200" ]] || fail "Frontend SOC runner API proxy returned HTTP ${proxy_http}"
        "$VENV_PYTHON" - "$tmp" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
types = {row["tsoc_record_type"] for row in d["results"]}
assert {"soc_analysis", "soc_analysis_audit", "soc_investigation_defender", "soc_investigation_hunter", "soc_investigation_judge"} <= types
PY
        rm -f "$tmp" "$cookie_jar"
        pass "Authenticated UI page and frontend Runbook + SOC runner proxies"
    else
        info "Frontend is stopped; authenticated UI checks skipped"
    fi
else
    info "Backend is stopped; live API checks skipped (restore contracts still passed)"
fi

pass "Demo-data smoke test completed without modifying the installed database"
