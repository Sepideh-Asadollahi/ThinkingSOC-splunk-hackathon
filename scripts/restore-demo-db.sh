#!/usr/bin/env bash
# Restore the full demo PostgreSQL backup into tsoc-postgres (use on any server).
# Source: backend/data/demo/postgres_dump/tsoc_demo.sql (DROP + recreate + data).
# Set FORCE_DEMO_RESTORE=true to restore even when DB already looks complete.
# Appends to logs/demo-restore.log for troubleshooting.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND="${REPO_ROOT}/backend"
DUMP_FILE="${BACKEND}/data/demo/postgres_dump/tsoc_demo.sql"
PSQL_LOG="${REPO_ROOT}/logs/demo-restore-psql.log"
RESTORE_LOG="${REPO_ROOT}/logs/demo-restore.log"

_rlog() {
    local line="[$(date -Iseconds 2>/dev/null || date)] $*"
    echo "$line" >>"$RESTORE_LOG"
    echo "$*"
}

_rlog_section() {
    echo "" >>"$RESTORE_LOG"
    echo "--- $* ---" >>"$RESTORE_LOG"
    echo "[INFO] $*"
}

_rlog_tail() {
    local label="$1" file="$2" n="${3:-30}"
    [[ -f "$file" ]] || return 0
    echo "" >>"$RESTORE_LOG"
    echo "--- tail ${label} ---" >>"$RESTORE_LOG"
    tail -n "$n" "$file" >>"$RESTORE_LOG" 2>/dev/null || true
}

mkdir -p "${REPO_ROOT}/logs"
{
    echo "================================================================"
    echo "Manual restore: scripts/restore-demo-db.sh"
    echo "started: $(date -Iseconds 2>/dev/null || date)"
    echo "REPO_ROOT=${REPO_ROOT}"
    echo "FORCE_DEMO_RESTORE=${FORCE_DEMO_RESTORE:-false}"
    echo "================================================================"
} >>"$RESTORE_LOG"

stop_app_services() {
    if systemctl is-active --quiet tsoc-backend 2>/dev/null \
        || systemctl is-active --quiet tsoc-frontend 2>/dev/null; then
        _rlog "Stopping tsoc-backend and tsoc-frontend before restore …"
        systemctl stop tsoc-frontend tsoc-backend 2>/dev/null || true
    elif [[ -f "${REPO_ROOT}/logs/backend.pid" ]]; then
        _rlog "Stopping background backend/frontend before restore …"
        local pid name
        for name in backend frontend; do
            pid="$(cat "${REPO_ROOT}/logs/${name}.pid" 2>/dev/null || true)"
            if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            fi
            rm -f "${REPO_ROOT}/logs/${name}.pid"
        done
    fi
    sleep 2
}

terminate_db_sessions() {
    _rlog "Terminating other PostgreSQL sessions on database tsoc …"
    docker exec tsoc-postgres psql -U tsoc -d tsoc -q -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'tsoc' AND pid <> pg_backend_pid();" \
        2>/dev/null || true
    sleep 1
}

log_pg_counts() {
    local label="$1"
    _rlog_section "$label"
    docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc \
        "SELECT 'users='||COUNT(*)::text FROM tsoc_users
         UNION ALL SELECT 'records='||COUNT(*)::text FROM tsoc_records
         UNION ALL SELECT 'analyses='||COUNT(*)::text FROM tsoc_records
           WHERE tsoc_record_type IN ('soc_analysis','observability_analysis')
         UNION ALL SELECT 'rag='||COUNT(*)::text FROM tsoc_rag_documents
         UNION ALL SELECT 'findings='||COUNT(*)::text FROM graph_findings;" \
        2>/dev/null | grep -viE 'WARNING|NOTICE' | while read -r line; do
            [[ -n "$line" ]] && _rlog "  ${line}"
        done
}

log_token_status() {
    _rlog_section "Token status (lengths only)"
    local be fe
    be="$(grep -E '^TSOC_INGEST_TOKEN=' "${REPO_ROOT}/backend/.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    fe="$(grep -E '^TSOC_INGEST_TOKEN=' "${REPO_ROOT}/frontend/.env.local" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    _rlog "  backend TSOC_INGEST_TOKEN len=${#be} frontend len=${#fe}"
    if [[ -n "$be" && "$be" != "$fe" ]]; then
        _rlog "WARN: token mismatch — sync frontend/.env.local and restart tsoc-frontend"
    fi
}

sync_frontend_ingest_token() {
    local backend_env="${REPO_ROOT}/backend/.env"
    local frontend_env="${REPO_ROOT}/frontend/.env.local"
    [[ -f "$backend_env" && -f "$frontend_env" ]] || return 0
    local tok
    tok="$(grep -E '^TSOC_INGEST_TOKEN=' "$backend_env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    [[ -n "$tok" ]] || return 0
    if grep -qE '^[[:space:]]*TSOC_INGEST_TOKEN=' "$frontend_env" 2>/dev/null; then
        sed -i "s|^[[:space:]]*TSOC_INGEST_TOKEN=.*|TSOC_INGEST_TOKEN=${tok}|" "$frontend_env"
    else
        echo "TSOC_INGEST_TOKEN=${tok}" >>"$frontend_env"
    fi
    _rlog "Synced TSOC_INGEST_TOKEN backend → frontend/.env.local"
}

verify_api_visibility() {
    local token tmp http_code triage_count graph_count
    token="$(grep -E '^CORRELATION_BEARER_TOKEN=' "${REPO_ROOT}/backend/.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    if [[ -z "$token" ]]; then
        token="$(grep -E '^TSOC_INGEST_TOKEN=' "${REPO_ROOT}/backend/.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    fi
    _rlog_section "API visibility (backend direct :9876)"
    if ! curl -sf --noproxy '*' --max-time 5 http://127.0.0.1:9876/health &>/dev/null; then
        _rlog "WARN: Backend /health not reachable"
        return 1
    fi
    _rlog "  backend /health: OK"
    tmp="$(mktemp)"
    if [[ -n "$token" ]]; then
        http_code="$(curl -sS --noproxy '*' --max-time 15 -H "Authorization: Bearer ${token}" \
            -o "$tmp" -w "%{http_code}" "http://127.0.0.1:9876/api/v1/triage/queue?track=all&limit=50" 2>/dev/null || echo "000")"
    else
        http_code="$(curl -sS --noproxy '*' --max-time 15 \
            -o "$tmp" -w "%{http_code}" "http://127.0.0.1:9876/api/v1/triage/queue?track=all&limit=50" 2>/dev/null || echo "000")"
    fi
    if [[ "$http_code" == "200" ]]; then
        triage_count="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('count','?'))" "$tmp" 2>/dev/null || echo "?")"
        _rlog "  GET /api/v1/triage/queue → HTTP 200 count=${triage_count}"
    else
        _rlog "WARN: GET /api/v1/triage/queue → HTTP ${http_code}"
        _rlog_tail "triage response" "$tmp" 5
    fi
    rm -f "$tmp"

    # UI proxy probe
    _rlog_section "UI proxy (:3000 login + /api/backend/triage/queue)"
    if curl -sf --noproxy '*' --max-time 5 http://127.0.0.1:3000/ &>/dev/null; then
        local cookie_jar demo_user demo_pass login_http proxy_http
        cookie_jar="$(mktemp)"
        demo_user="$(grep -E '^TSOC_DEMO_USER=' "${REPO_ROOT}/frontend/.env.local" 2>/dev/null | head -1 | cut -d= -f2- || echo admin)"
        demo_pass="$(grep -E '^TSOC_DEMO_PASSWORD=' "${REPO_ROOT}/frontend/.env.local" 2>/dev/null | head -1 | cut -d= -f2- || echo 123456@a)"
        login_http="$(curl -sS --noproxy '*' -c "$cookie_jar" -o /dev/null -w '%{http_code}' \
            -X POST http://127.0.0.1:3000/api/auth/login \
            -H 'Content-Type: application/json' \
            -d "{\"username\":\"${demo_user}\",\"password\":\"${demo_pass}\"}" 2>/dev/null || echo "000")"
        _rlog "  POST /api/auth/login → HTTP ${login_http}"
        if [[ "$login_http" == "200" ]]; then
            tmp="$(mktemp)"
            proxy_http="$(curl -sS --noproxy '*' -b "$cookie_jar" -o "$tmp" -w '%{http_code}' \
                "http://127.0.0.1:3000/api/backend/triage/queue?track=all&limit=50" 2>/dev/null || echo "000")"
            triage_count="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('count','?'))" "$tmp" 2>/dev/null || echo "?")"
            _rlog "  GET /api/backend/triage/queue → HTTP ${proxy_http} count=${triage_count}"
            rm -f "$tmp"
        else
            _rlog "WARN: login failed — open http://<host>:3000/login in browser"
        fi
        rm -f "$cookie_jar"
    else
        _rlog "WARN: frontend :3000 not reachable"
    fi
    _rlog "Full log: ${RESTORE_LOG}"
    _rlog "Also run: bash ${REPO_ROOT}/scripts/diagnose-demo-ui.sh"
}

restart_services() {
    sync_frontend_ingest_token
    log_token_status

    if systemctl list-unit-files tsoc-backend.service &>/dev/null 2>&1; then
        _rlog "Restarting tsoc-backend and tsoc-frontend (systemd) …"
        systemctl restart tsoc-backend tsoc-frontend 2>/dev/null || true
        for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
            if curl -sf --noproxy '*' http://127.0.0.1:9876/health &>/dev/null; then
                _rlog "Backend healthy after restart"
                verify_api_visibility
                return 0
            fi
            sleep 5
        done
        _rlog "WARN: Backend /health not ready yet (embedding may still load)"
    elif [[ -f "${REPO_ROOT}/scripts/start-tsoc-services.sh" ]]; then
        _rlog "Restarting background services …"
        sudo bash "${REPO_ROOT}/scripts/start-tsoc-services.sh" || true
        verify_api_visibility
    fi
}

if [[ ! -f "$DUMP_FILE" ]]; then
    echo "[ERROR] Missing demo backup: ${DUMP_FILE}" >&2
    exit 1
fi
if ! docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
    echo "[ERROR] tsoc-postgres is not ready. Start: cd ${BACKEND} && docker compose up -d" >&2
    exit 1
fi

_rlog "Dump file: ${DUMP_FILE} ($(du -h "$DUMP_FILE" | cut -f1), $(wc -l < "$DUMP_FILE") lines)"
log_pg_counts "Row counts BEFORE restore"
stop_app_services
terminate_db_sessions

_t0=$(date +%s)
_rlog "Restoring demo database from ${DUMP_FILE} …"
if ! docker exec -i tsoc-postgres psql -U tsoc -d tsoc -v ON_ERROR_STOP=1 -q < "$DUMP_FILE" >"$PSQL_LOG" 2>&1; then
    _rlog "ERROR: Restore failed — see ${PSQL_LOG}"
    _rlog_tail "psql output" "$PSQL_LOG" 40
    tail -20 "$PSQL_LOG" >&2 || true
    exit 1
fi
_elapsed=$(( $(date +%s) - _t0 ))
_rlog "Restore complete in ${_elapsed}s (details: ${PSQL_LOG})"

log_pg_counts "Row counts AFTER restore"

_rlog "Ensuring Neo4j correlation graph matches restored Postgres demo …"
if bash "${REPO_ROOT}/scripts/seed-correlation-demo.sh" >>"$RESTORE_LOG" 2>&1; then
    _rlog "Correlation demo baseline ready (Neo4j alerts + graph_findings if needed)."
else
    _rlog "WARN: correlation demo seed failed — run: bash scripts/seed-correlation-demo.sh"
fi

restart_services
