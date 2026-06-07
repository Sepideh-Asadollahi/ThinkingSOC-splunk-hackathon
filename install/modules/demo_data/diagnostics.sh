#!/usr/bin/env bash
# Demo data — extended diagnostics for demo-restore.log (no secrets logged).

_demo_env_token_len() {
    local file="$1" key="$2"
    local val
    val="$(grep -E "^${key}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    echo "${#val}"
}

_demo_log_runtime_context() {
    _demo_log_section "Runtime context"
    _demo_log "  hostname=$(hostname 2>/dev/null || echo '?')"
    _demo_log "  user=$(id -un 2>/dev/null || echo '?')"
    _demo_log "  FORCE_DEMO_RESTORE=${FORCE_DEMO_RESTORE:-false}"
    _demo_log "  SETUP_SYSTEMD=${SETUP_SYSTEMD:-false}"
    if command -v git &>/dev/null && [[ -d "${INSTALL_DIR}/.git" ]]; then
        _demo_log "  git_rev=$(git -C "${INSTALL_DIR}" rev-parse --short HEAD 2>/dev/null || echo '?')"
        _demo_log "  git_branch=$(git -C "${INSTALL_DIR}" branch --show-current 2>/dev/null || echo '?')"
    fi
    if [[ -f "$(_demo_dump_file)" ]]; then
        local dump mtime sha
        dump="$(_demo_dump_file)"
        mtime="$(stat -c '%y' "$dump" 2>/dev/null | cut -d. -f1 || echo '?')"
        sha="$(sha256sum "$dump" 2>/dev/null | cut -c1-16 || echo '?')"
        _demo_log "  dump_file mtime=${mtime} sha256_prefix=${sha}"
    fi
}

_demo_log_token_status() {
    local backend_env="${INSTALL_DIR}/backend/.env"
    local frontend_env="${INSTALL_DIR}/frontend/.env.local"
    local be_len fe_len corr_len be_tok fe_tok

    _demo_log_section "Auth / token status (lengths only — no secrets)"
    [[ -f "$backend_env" ]] || _demo_log_warn "  backend/.env missing"
    [[ -f "$frontend_env" ]] || _demo_log_warn "  frontend/.env.local missing"

    be_len="$(_demo_env_token_len "$backend_env" "TSOC_INGEST_TOKEN")"
    fe_len="$(_demo_env_token_len "$frontend_env" "TSOC_INGEST_TOKEN")"
    corr_len="$(_demo_env_token_len "$backend_env" "CORRELATION_BEARER_TOKEN")"
    _demo_log "  TSOC_INGEST_TOKEN backend_len=${be_len} frontend_len=${fe_len}"
    _demo_log "  CORRELATION_BEARER_TOKEN backend_len=${corr_len}"

    if [[ "$be_len" -gt 0 && "$fe_len" -gt 0 ]]; then
        be_tok="$(grep -E '^TSOC_INGEST_TOKEN=' "$backend_env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
        fe_tok="$(grep -E '^TSOC_INGEST_TOKEN=' "$frontend_env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
        if [[ "$be_tok" == "$fe_tok" ]]; then
            _demo_log "  Token sync: OK (backend == frontend)"
        else
            _demo_log_warn "  Token sync: MISMATCH — UI proxy gets 401/403 from backend"
            _demo_log_warn "  Fix: run install token sync or: sed frontend/.env.local + systemctl restart tsoc-frontend"
        fi
    elif [[ "$be_len" -gt 0 && "$fe_len" -eq 0 ]]; then
        _demo_log_warn "  Token sync: backend has token, frontend empty — UI will fail API calls"
    elif [[ "$be_len" -eq 0 ]]; then
        _demo_log "  Ingest auth: disabled (empty TSOC_INGEST_TOKEN)"
    fi

    if [[ -f "$frontend_env" ]]; then
        local demo_user demo_pass_len
        demo_user="$(grep -E '^TSOC_DEMO_USER=' "$frontend_env" 2>/dev/null | head -1 | cut -d= -f2- || echo admin)"
        demo_pass_len="$(_demo_env_token_len "$frontend_env" "TSOC_DEMO_PASSWORD")"
        _demo_log "  UI login user=${demo_user:-admin} password_set=$([[ ${demo_pass_len:-0} -gt 0 ]] && echo yes || echo 'default(123456@a)')"
        _demo_log "  UI requires login at :3000/login before /analysis shows data"
    fi
}

_demo_log_services_status() {
    _demo_log_section "Service / port status"
    if [[ "${SETUP_SYSTEMD:-false}" == true ]]; then
        local be fe pg
        be="$(systemctl is-active tsoc-backend 2>/dev/null || echo inactive)"
        fe="$(systemctl is-active tsoc-frontend 2>/dev/null || echo inactive)"
        _demo_log "  systemd tsoc-backend=${be} tsoc-frontend=${fe}"
    else
        _demo_log "  systemd: not used (SETUP_SYSTEMD=false)"
        if [[ -f "${INSTALL_DIR}/logs/backend.pid" ]]; then
            _demo_log "  background backend.pid present"
        fi
    fi
    if declare -F _tsoc_tcp_port_in_use &>/dev/null; then
        if _tsoc_tcp_port_in_use 9876 2>/dev/null; then
            _demo_log "  port 9876 (backend): listening"
        else
            _demo_log_warn "  port 9876 (backend): not listening"
        fi
        if _tsoc_tcp_port_in_use 3000 2>/dev/null; then
            _demo_log "  port 3000 (frontend): listening"
        else
            _demo_log_warn "  port 3000 (frontend): not listening"
        fi
    fi
    if docker ps --filter "name=^tsoc-postgres$" --format '{{.Status}}' 2>/dev/null | grep -q .; then
        _demo_log "  docker tsoc-postgres: $(docker ps --filter "name=^tsoc-postgres$" --format '{{.Status}}' 2>/dev/null | head -1)"
    else
        _demo_log_warn "  docker tsoc-postgres: not running"
    fi
}

_demo_log_bundle_complete_audit() {
    local lines has_users users analyses findings rag reason=""
    _demo_log_section "Bundle-complete audit (skip restore when all pass)"
    lines="$(_demo_query_postgres_counts)" || {
        _demo_log_warn "  Cannot query PostgreSQL — bundle incomplete"
        return 1
    }
    has_users="$(echo "$lines" | sed -n '1p' | tr -d '[:space:]')"
    users="$(echo "$lines" | sed -n '2p' | tr -d '[:space:]')"
    analyses="$(echo "$lines" | sed -n '3p' | tr -d '[:space:]')"
    findings="$(echo "$lines" | sed -n '4p' | tr -d '[:space:]')"
    rag="$(echo "$lines" | sed -n '5p' | tr -d '[:space:]')"

    _demo_log "  criterion tsoc_users table exists: ${has_users}"
    _demo_log "  criterion users>=7: ${users:-?} $([[ -n "$users" && "$users" -ge 7 ]] 2>/dev/null && echo PASS || echo FAIL)"
    _demo_log "  criterion analyses>=1: ${analyses:-?} $([[ -n "$analyses" && "$analyses" -ge 1 ]] 2>/dev/null && echo PASS || echo FAIL)"
    _demo_log "  criterion graph_findings>=1: ${findings:-?} $([[ -n "$findings" && "$findings" -ge 1 ]] 2>/dev/null && echo PASS || echo FAIL)"
    _demo_log "  criterion rag>=1: ${rag:-?} $([[ -n "$rag" && "$rag" -ge 1 ]] 2>/dev/null && echo PASS || echo FAIL)"

    if _demo_db_bundle_complete; then
        _demo_log "  Result: COMPLETE — install may skip pg_dump restore (use FORCE_DEMO_RESTORE=true to override)"
        return 0
    fi
    [[ "$has_users" != "t" ]] && reason+="missing tsoc_users; "
    [[ -z "$users" || "$users" -lt 7 ]] 2>/dev/null && reason+="users<7; "
    [[ -z "$analyses" || "$analyses" -lt 1 ]] 2>/dev/null && reason+="analyses<1; "
    [[ -z "$findings" || "$findings" -lt 1 ]] 2>/dev/null && reason+="findings<1; "
    [[ -z "$rag" || "$rag" -lt 1 ]] 2>/dev/null && reason+="rag<1; "
    _demo_log "  Result: INCOMPLETE — will restore (${reason:-unknown})"
    return 1
}

_demo_log_record_type_breakdown() {
    if ! docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
        return 1
    fi
    _demo_log_section "tsoc_records by type"
    local out
    out="$(docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc \
        "SELECT tsoc_record_type||'='||COUNT(*)::text FROM tsoc_records
         GROUP BY 1 ORDER BY 2 DESC, 1;" 2>/dev/null | grep -viE 'WARNING|NOTICE' || true)"
    if [[ -z "$out" ]]; then
        _demo_log "  (no tsoc_records rows or table missing)"
        return 0
    fi
    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        _demo_log "  ${line}"
    done <<< "$out"
}

_demo_log_pg_activity() {
    if ! docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
        return 1
    fi
    _demo_log_section "PostgreSQL sessions on database tsoc"
    local out count
    count="$(docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc \
        "SELECT COUNT(*) FROM pg_stat_activity WHERE datname='tsoc';" 2>/dev/null | tr -d '[:space:]' || echo "?")"
    _demo_log "  active_sessions=${count}"
    out="$(docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc \
        "SELECT COALESCE(application_name,'?')||' pid='||pid||' state='||state
         FROM pg_stat_activity WHERE datname='tsoc' AND pid <> pg_backend_pid()
         LIMIT 10;" 2>/dev/null | grep -viE 'WARNING|NOTICE' || true)"
    if [[ -n "$out" ]]; then
        while IFS= read -r line; do
            [[ -n "$line" ]] || continue
            _demo_log "  ${line}"
        done <<< "$out"
    else
        _demo_log "  (no other sessions — safe for DROP/restore)"
    fi
}

_demo_log_curl_body_preview() {
    local label="$1" http_code="$2" body_file="$3"
    local preview
    preview="$(head -c 240 "$body_file" 2>/dev/null | tr '\n' ' ' || true)"
    _demo_log "  ${label} HTTP ${http_code} body_preview=${preview}"
}

_demo_log_ui_proxy_check() {
    local demo_user demo_pass frontend_env cookie_jar login_http proxy_http proxy_count
    frontend_env="${INSTALL_DIR}/frontend/.env.local"
    demo_user="$(grep -E '^TSOC_DEMO_USER=' "$frontend_env" 2>/dev/null | head -1 | cut -d= -f2- || echo admin)"
    demo_pass="$(grep -E '^TSOC_DEMO_PASSWORD=' "$frontend_env" 2>/dev/null | head -1 | cut -d= -f2- || echo 123456@a)"

    _demo_log_section "UI proxy path (:3000 — requires login session)"
    if ! curl -sf --noproxy '*' --max-time 5 http://127.0.0.1:3000/ &>/dev/null; then
        _demo_log_warn "  Frontend :3000 not reachable — skip UI proxy test"
        return 1
    fi

    cookie_jar="$(mktemp)"
    login_http="$(curl -sS --noproxy '*' -c "$cookie_jar" -o /dev/null -w '%{http_code}' \
        -X POST http://127.0.0.1:3000/api/auth/login \
        -H 'Content-Type: application/json' \
        -d "{\"username\":\"${demo_user}\",\"password\":\"${demo_pass}\"}" 2>/dev/null || echo "000")"
    _demo_log "  POST /api/auth/login user=${demo_user} → HTTP ${login_http}"
    if [[ "$login_http" != "200" ]]; then
        _demo_log_warn "  UI login failed — browser /analysis will be empty until login at :3000/login"
        rm -f "$cookie_jar"
        return 1
    fi

    local tmp
    tmp="$(mktemp)"
    proxy_http="$(curl -sS --noproxy '*' -b "$cookie_jar" -o "$tmp" -w '%{http_code}' \
        "http://127.0.0.1:3000/api/backend/triage/queue?track=all&limit=50" 2>/dev/null || echo "000")"
    proxy_count="$(python3 -c "
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print(d.get('count', len(d.get('results') or [])))
except Exception as e:
    print('parse_err:'+str(e)[:40])
" "$tmp" 2>/dev/null || echo "?")"

    if [[ "$proxy_http" == "200" ]]; then
        _demo_log "  GET /api/backend/triage/queue → HTTP 200, count=${proxy_count} (what Analysis page loads)"
        if [[ "$proxy_count" == "0" ]]; then
            _demo_log_warn "  UI proxy returned empty queue — compare with backend direct :9876 test"
        fi
    else
        _demo_log_warn "  GET /api/backend/triage/queue → HTTP ${proxy_http}"
        _demo_log_curl_body_preview "UI proxy" "$proxy_http" "$tmp"
    fi
    rm -f "$cookie_jar" "$tmp"
    return 0
}

_demo_log_full_diagnostics() {
    local label="${1:-Full diagnostics summary}"
    _demo_log_section "${label}"
    _demo_log_token_status
    _demo_log_services_status
    _demo_log_bundle_complete_audit || true
    _demo_log_postgres_counts "PostgreSQL counts (diagnostic)" || true
    _demo_log_record_type_breakdown || true
}
