#!/usr/bin/env bash
# Demo data — ingest token sync and post-restore API visibility checks.

_demo_sync_ingest_token_to_frontend() {
    _demo_log_section "Sync TSOC_INGEST_TOKEN backend → frontend"
    local backend_env="$INSTALL_DIR/backend/.env"
    local frontend_env="$INSTALL_DIR/frontend/.env.local"
    local be_before fe_before tok

    be_before="$(_demo_env_token_len "$backend_env" "TSOC_INGEST_TOKEN")"
    fe_before="$(_demo_env_token_len "$frontend_env" "TSOC_INGEST_TOKEN")"
    _demo_log "  before: backend_len=${be_before} frontend_len=${fe_before}"

    if declare -F _sync_frontend_ingest_token_from_backend >/dev/null 2>&1; then
        _sync_frontend_ingest_token_from_backend
    elif [[ -f "$backend_env" && -f "$frontend_env" ]]; then
        tok="$(grep -E '^TSOC_INGEST_TOKEN=' "$backend_env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
        if [[ -n "$tok" ]] && declare -F _upsert_env_line >/dev/null 2>&1; then
            _upsert_env_line "$frontend_env" "TSOC_INGEST_TOKEN" "$tok"
        fi
    else
        _demo_log_warn "  skipped — missing backend/.env or frontend/.env.local"
        return 0
    fi

    local fe_after
    fe_after="$(_demo_env_token_len "$frontend_env" "TSOC_INGEST_TOKEN")"
    _demo_log "  after: frontend_len=${fe_after}"
    if [[ "$be_before" -gt 0 && "$fe_after" -eq "$be_before" ]]; then
        _demo_log "  Synced TSOC_INGEST_TOKEN (required for UI API proxy)"
    elif [[ "$be_before" -eq 0 ]]; then
        _demo_log "  No backend ingest token — sync not needed"
    else
        _demo_log_warn "  Sync may have failed — verify frontend/.env.local manually"
    fi
}

_demo_backend_bearer_token() {
    local tok
    tok="$(grep -E '^CORRELATION_BEARER_TOKEN=' "${INSTALL_DIR}/backend/.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    if [[ -n "$tok" ]]; then
        echo "$tok"
        return 0
    fi
    grep -E '^TSOC_INGEST_TOKEN=' "${INSTALL_DIR}/backend/.env" 2>/dev/null | head -1 | cut -d= -f2- || true
}

_demo_curl_backend_json() {
    local url="$1"
    local out_file="$2"
    local token
    token="$(_demo_backend_bearer_token)"
    if [[ -n "$token" ]]; then
        curl -sS --noproxy '*' --max-time 15 \
            -H "Authorization: Bearer ${token}" \
            -o "$out_file" -w "%{http_code}" "$url" 2>/dev/null || echo "000"
    else
        curl -sS --noproxy '*' --max-time 15 \
            -o "$out_file" -w "%{http_code}" "$url" 2>/dev/null || echo "000"
    fi
}

_demo_log_api_endpoint() {
    local label="$1" url="$2"
    local tmp http_code count_key count
    tmp="$(mktemp)"
    http_code="$(_demo_curl_backend_json "$url" "$tmp")"
    if [[ "$http_code" == "401" || "$http_code" == "403" ]]; then
        _demo_log_warn "  ${label} → HTTP ${http_code} (Bearer token missing/invalid)"
        _demo_log_curl_body_preview "$label" "$http_code" "$tmp"
    elif [[ "$http_code" != "200" ]]; then
        _demo_log_warn "  ${label} → HTTP ${http_code}"
        _demo_log_curl_body_preview "$label" "$http_code" "$tmp"
    else
        count="$(python3 -c "
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    if 'count' in d: print(d['count'])
    elif 'total' in d: print(d['total'])
    elif 'results' in d: print(len(d['results'] or []))
    elif 'items' in d: print(len(d['items'] or []))
    else: print('ok')
except Exception as e:
    print('?')
" "$tmp" 2>/dev/null || echo "?")"
        _demo_log "  ${label} → HTTP 200, value=${count}"
    fi
    rm -f "$tmp"
}

_demo_log_api_visibility() {
    local label="${1:-API visibility (what the UI reads)}"
    _demo_log_section "${label}"

    if declare -F _demo_log_token_status &>/dev/null 2>&1; then
        _demo_log_token_status
    fi

    if ! curl -sf --noproxy '*' --max-time 5 http://127.0.0.1:9876/health &>/dev/null; then
        _demo_log_warn "  backend :9876 /health not reachable — skip API probes (start tsoc-backend first)"
        if declare -F _demo_log_services_status &>/dev/null 2>&1; then
            _demo_log_services_status
        fi
        return 1
    fi
    _demo_log "  backend /health: OK"

    _demo_log_api_endpoint "GET /api/v1/triage/queue?track=all&limit=50 (Analysis)" \
        "http://127.0.0.1:9876/api/v1/triage/queue?track=all&limit=50"
    _demo_log_api_endpoint "GET /api/v1/graph/findings?limit=10 (Correlation)" \
        "http://127.0.0.1:9876/api/v1/graph/findings?limit=10&offset=0"
    _demo_log_api_endpoint "GET /api/v1/graph/health (Neo4j+PG)" \
        "http://127.0.0.1:9876/api/v1/graph/health"

    if declare -F _demo_log_ui_proxy_check &>/dev/null 2>&1; then
        _demo_log_ui_proxy_check || true
    fi
    return 0
}
