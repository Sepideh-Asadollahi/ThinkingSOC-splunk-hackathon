#!/usr/bin/env bash
# Diagnose demo data visibility: PostgreSQL counts, backend API, UI proxy (session + token).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_ENV="${REPO_ROOT}/backend/.env"
FRONTEND_ENV="${REPO_ROOT}/frontend/.env.local"
COOKIE_JAR="$(mktemp)"
trap 'rm -f "$COOKIE_JAR"' EXIT

DEMO_USER="${TSOC_DEMO_USER:-admin}"
DEMO_PASS="${TSOC_DEMO_PASSWORD:-123456@a}"

section() { echo ""; echo "=== $* ==="; }

section "PostgreSQL row counts"
if docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
    docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc \
        "SELECT 'analyses(soc+obs)='||COUNT(*)::text FROM tsoc_records
           WHERE tsoc_record_type IN ('soc_analysis','observability_analysis')
         UNION ALL SELECT 'graph_findings='||COUNT(*)::text FROM graph_findings
         UNION ALL SELECT 'rag='||COUNT(*)::text FROM tsoc_rag_documents;" \
        2>/dev/null | grep -viE 'WARNING|NOTICE' | sed 's/^/  /'
else
    echo "  [WARN] tsoc-postgres not ready"
fi

TOKEN=""
if [[ -f "$BACKEND_ENV" ]]; then
    TOKEN="$(grep -E '^TSOC_INGEST_TOKEN=' "$BACKEND_ENV" 2>/dev/null | head -1 | cut -d= -f2- || true)"
fi
FE_TOKEN=""
if [[ -f "$FRONTEND_ENV" ]]; then
    FE_TOKEN="$(grep -E '^TSOC_INGEST_TOKEN=' "$FRONTEND_ENV" 2>/dev/null | head -1 | cut -d= -f2- || true)"
fi

section "Ingest token sync"
echo "  backend TSOC_INGEST_TOKEN length: ${#TOKEN}"
echo "  frontend TSOC_INGEST_TOKEN length: ${#FE_TOKEN}"
if [[ -n "$TOKEN" && "$TOKEN" != "$FE_TOKEN" ]]; then
    echo "  [FAIL] Tokens differ — UI proxy will get 401 from backend"
    echo "  Fix: sed -i \"s|^TSOC_INGEST_TOKEN=.*|TSOC_INGEST_TOKEN=\${TOKEN}|\" frontend/.env.local"
    echo "       sudo systemctl restart tsoc-frontend"
elif [[ -n "$TOKEN" ]]; then
    echo "  [OK] Tokens match"
else
    echo "  [OK] No ingest token configured (backend open)"
fi

section "Backend direct (curl :9876 — what you already tested)"
if curl -sf --noproxy '*' --max-time 5 http://127.0.0.1:9876/health &>/dev/null; then
    echo "  /health: OK"
    CURL_ARGS=(--noproxy '*' -sS --max-time 15)
    if [[ -n "$TOKEN" ]]; then
        CURL_ARGS+=(-H "Authorization: Bearer ${TOKEN}")
    fi
    COUNT="$(curl "${CURL_ARGS[@]}" "http://127.0.0.1:9876/api/v1/triage/queue?track=all&limit=50" \
        | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('count','?'))" 2>/dev/null || echo "?")"
    echo "  GET /api/v1/triage/queue count=${COUNT}"
    if [[ "$COUNT" == "0" ]]; then
        echo "  [WARN] Backend queue empty — run backup on source with more analyses first"
    elif [[ "$COUNT" != "?" ]]; then
        echo "  [OK] Backend has data (Analysis page should show ${COUNT} row(s) if UI proxy works)"
    fi
else
    echo "  [FAIL] Backend /health not responding on :9876"
fi

section "UI proxy (curl :3000 — requires login session)"
if ! curl -sf --noproxy '*' --max-time 5 http://127.0.0.1:3000/ &>/dev/null; then
    echo "  [FAIL] Frontend not responding on :3000"
    exit 0
fi

LOGIN_HTTP="$(curl -sS --noproxy '*' -c "$COOKIE_JAR" -o /dev/null -w '%{http_code}' \
    -X POST http://127.0.0.1:3000/api/auth/login \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"${DEMO_USER}\",\"password\":\"${DEMO_PASS}\"}")"
if [[ "$LOGIN_HTTP" != "200" ]]; then
    echo "  [FAIL] Login HTTP ${LOGIN_HTTP} (user=${DEMO_USER})"
    echo "  UI shows empty pages when not logged in — open http://<host>:3000/login first"
    echo "  Default: admin / 123456@a (or TSOC_DEMO_USER / TSOC_DEMO_PASSWORD in frontend/.env.local)"
    exit 0
fi
echo "  Login: OK (${DEMO_USER})"

PROXY_HTTP="$(curl -sS --noproxy '*' -b "$COOKIE_JAR" -o /tmp/tsoc-proxy-triage.json -w '%{http_code}' \
    "http://127.0.0.1:3000/api/backend/triage/queue?track=all&limit=50")"
PROXY_COUNT="$(python3 -c "
import json
try:
    d=json.load(open('/tmp/tsoc-proxy-triage.json'))
    print(d.get('count', len(d.get('results') or [])))
except Exception:
    print('?')
" 2>/dev/null || echo "?")"
rm -f /tmp/tsoc-proxy-triage.json

echo "  GET /api/backend/triage/queue → HTTP ${PROXY_HTTP}, count=${PROXY_COUNT}"
if [[ "$PROXY_HTTP" == "200" && "$PROXY_COUNT" != "0" && "$PROXY_COUNT" != "?" ]]; then
    echo "  [OK] UI proxy path works — browser should show data after login"
elif [[ "$PROXY_HTTP" == "401" ]]; then
    echo "  [FAIL] Proxy 401 — not logged in or session cookie invalid"
elif [[ "$PROXY_HTTP" == "403" ]]; then
    echo "  [FAIL] Proxy/backend 403 — TSOC_INGEST_TOKEN mismatch; restart tsoc-frontend"
elif [[ "$PROXY_COUNT" == "0" ]]; then
    echo "  [WARN] Proxy returned empty queue despite backend data — check frontend logs"
else
    echo "  [WARN] Unexpected proxy response HTTP ${PROXY_HTTP}"
fi

section "Browser checklist"
echo "  1. Open http://<server-ip>:3000/login"
echo "  2. Login: ${DEMO_USER} / (see TSOC_DEMO_PASSWORD in frontend/.env.local)"
echo "  3. Go to /analysis — expect count=${COUNT:-?} from backend direct test"
echo "  Note: pg_dump backup has NO limits; if count=1, source DB only has 1 analysis."
