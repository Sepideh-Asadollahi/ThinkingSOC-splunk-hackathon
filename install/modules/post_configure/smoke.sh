#!/usr/bin/env bash
# Post-configure smoke test: live verification that integration works right now.

run_integration_configure_smoke() {
    local pass=0 fail=0 warn=0
    local backend_env="${INSTALL_DIR}/backend/.env"
    local frontend_env="${INSTALL_DIR}/frontend/.env.local"

    _pc_smoke_ok() { ok "  $1"; pass=$((pass + 1)); }
    _pc_smoke_fail() { err "  $1"; fail=$((fail + 1)); }
    _pc_smoke_warn() { warn "  $1"; warn=$((warn + 1)); }

    step "Integration verification (smoke test — live checks)"
    echo ""
    echo "  Purpose: confirm post-install integration works now (not just .env on disk)."
    echo "  Checks: config files, Splunk REST login, backend /health, MCP API if configured."
    echo ""

    if [[ ! -f "$backend_env" ]]; then
        _pc_smoke_fail "backend/.env missing"
        echo ""
        warn "Integration smoke: 0 passed, ${fail} failed"
        return 1
    fi
    _pc_smoke_ok "backend/.env present"

    local ingest_auto_analyze
    ingest_auto_analyze="$(_pc_env_get "$backend_env" TSOC_INGEST_AUTO_ANALYZE)"
    if [[ "$ingest_auto_analyze" == "true" ]]; then
        _pc_smoke_ok "TSOC_INGEST_AUTO_ANALYZE=true (Splunk/webhook alerts run triage after ingest)"
    else
        _pc_smoke_warn "TSOC_INGEST_AUTO_ANALYZE is not true — alerts ingest only (no auto triage)"
    fi

    if _tsoc_curl_ok "http://127.0.0.1:9876/health" 2>/dev/null; then
        _pc_smoke_ok "ThinkingSOC backend healthy (GET /health)"
    elif _tsoc_tcp_port_in_use 9876 2>/dev/null; then
        info "  Backend on :9876 — waiting for /health …"
        if _wait_for_backend_with_embedding_notice "http://127.0.0.1:9876/health" "Backend API" 90 2; then
            _pc_smoke_ok "ThinkingSOC backend healthy (GET /health, after wait)"
        else
            _pc_smoke_fail "Backend not healthy on http://127.0.0.1:9876/health — restart tsoc-backend"
        fi
    else
        _pc_smoke_fail "Backend not running on port 9876 — start or restart tsoc-backend before MCP checks"
    fi

    local splunk_home mgmt_url splunk_user splunk_pass mcp_token llm_key
    splunk_home="$(_pc_env_get "$backend_env" SPLUNK_HOME)"
    mgmt_url="$(_pc_env_get "$backend_env" SPLUNK_MGMT_URL)"
    splunk_user="$(_pc_env_get "$backend_env" SPLUNK_USERNAME)"
    splunk_pass="$(_pc_env_get "$backend_env" SPLUNK_PASSWORD)"
    mcp_token="$(_pc_env_get "$backend_env" SPLUNK_MCP_TOKEN)"
    llm_key="$(_pc_env_get "$backend_env" LITELLM_API_KEY)"
    local ingest_back ingest_front
    ingest_back="$(_pc_env_get "$backend_env" TSOC_INGEST_TOKEN)"

    if [[ -n "$splunk_home" ]]; then
        if [[ -d "$splunk_home" ]]; then
            _pc_smoke_ok "SPLUNK_HOME directory exists (${splunk_home})"
        else
            _pc_smoke_fail "SPLUNK_HOME path does not exist: ${splunk_home}"
        fi
        if [[ -x "${splunk_home}/bin/splunk" ]]; then
            _pc_smoke_ok "Splunk binary found (${splunk_home}/bin/splunk)"
        else
            _pc_smoke_warn "Splunk binary missing at ${splunk_home}/bin/splunk"
        fi
        if [[ -d "${splunk_home}/etc/apps/ThinkingSOC_Hackathon_Splunk_App" ]]; then
            _pc_smoke_ok "ThinkingSOC_Hackathon_Splunk_App installed under Splunk apps"
        else
            _pc_smoke_warn "ThinkingSOC_Hackathon_Splunk_App not in ${splunk_home}/etc/apps/ (install via wizard or README)"
        fi
    else
        _pc_smoke_warn "SPLUNK_HOME not set in backend/.env"
    fi

    if [[ -n "$mgmt_url" ]]; then
        _pc_smoke_ok "SPLUNK_MGMT_URL set (${mgmt_url})"
        _pc_parse_mgmt_url "$mgmt_url"
        if [[ -f "$frontend_env" ]]; then
            local fe_host fe_port
            fe_host="$(_pc_env_get "$frontend_env" NEXT_PUBLIC_TSOC_SPLUNK_HOST)"
            fe_port="$(_pc_env_get "$frontend_env" NEXT_PUBLIC_TSOC_SPLUNK_PORT)"
            if [[ "$fe_host" == "$_PC_SPLUNK_HOST" && "$fe_port" == "$_PC_SPLUNK_PORT" ]]; then
                _pc_smoke_ok "frontend Splunk host/port match management URL (${fe_host}:${fe_port})"
            else
                _pc_smoke_fail "frontend Splunk hints mismatch (got ${fe_host:-?}:${fe_port:-?}, expected ${_PC_SPLUNK_HOST}:${_PC_SPLUNK_PORT})"
            fi
        else
            _pc_smoke_warn "frontend/.env.local missing — cannot verify Splunk UI hints"
        fi
    else
        _pc_smoke_fail "SPLUNK_MGMT_URL not set in backend/.env"
    fi

    if [[ -n "$splunk_user" ]]; then
        if [[ -n "$splunk_pass" ]]; then
            _pc_smoke_ok "Splunk REST credentials present in backend/.env"
            local rest_out rest_rc=0
            rest_out="$(_pc_test_splunk_rest_login 2>&1)" || rest_rc=$?
            case "$rest_out" in
                OK)
                    _pc_smoke_ok "Splunk REST login succeeded (services/auth/login)"
                    ;;
                SKIP)
                    ;;
                *)
                    _pc_smoke_fail "Splunk REST login failed (${rest_out#FAIL:})"
                    ;;
            esac
        else
            _pc_smoke_fail "SPLUNK_USERNAME set but SPLUNK_PASSWORD is empty"
        fi
    else
        _pc_smoke_warn "SPLUNK_USERNAME not set — live Splunk REST/MCP checks skipped"
    fi

    local mcp_enabled
    mcp_enabled="$(_pc_env_get "$backend_env" TSOC_MCP_ENABLED)"
    if [[ "${mcp_enabled,,}" == "true" ]]; then
        _pc_smoke_ok "TSOC_MCP_ENABLED=true"
    else
        _pc_smoke_warn "TSOC_MCP_ENABLED is not true"
    fi

    if [[ -n "$mcp_token" ]]; then
        _pc_smoke_ok "SPLUNK_MCP_TOKEN set in backend/.env"
        local mcp_out mcp_rc=0
        mcp_out="$(_pc_test_mcp_status_api "http://127.0.0.1:9876" 2>&1)" || mcp_rc=$?
        case "$mcp_out" in
            OK:*)
                _pc_smoke_ok "Backend MCP status: connected (${mcp_out#OK:})"
                ;;
            SKIP:*)
                _pc_smoke_warn "Backend not reachable — MCP API check skipped (start tsoc-backend)"
                ;;
            WARN:not_connected:*)
                _pc_smoke_warn "MCP configured but not connected (${mcp_out#WARN:not_connected:})"
                ;;
            WARN:not_configured:*)
                _pc_smoke_warn "MCP token present but API reports not configured (${mcp_out#WARN:not_configured:})"
                ;;
            FAIL:*)
                _pc_smoke_fail "MCP status API error (${mcp_out#FAIL:})"
                ;;
            *)
                _pc_smoke_warn "MCP status check: ${mcp_out:-unknown}"
                ;;
        esac
    elif [[ -n "$splunk_user" ]]; then
        _pc_smoke_warn "SPLUNK_MCP_TOKEN empty — run: ${VENV_PYTHON:-backend/.venv/bin/python} scripts/mint_splunk_mcp_token.py"
    fi

    local llm_model
    llm_model="$(_pc_env_get "$backend_env" LITELLM_MODEL)"
    if [[ -n "$llm_key" ]]; then
        _pc_smoke_ok "LITELLM_API_KEY set in backend/.env"
        if [[ -n "$llm_model" ]]; then
            _pc_smoke_ok "LITELLM_MODEL set (${llm_model})"
        else
            _pc_smoke_warn "LITELLM_MODEL empty — set a model id in backend/.env"
        fi
    else
        _pc_smoke_fail "LITELLM_API_KEY required — SOC analysis depends on LiteLLM"
        [[ -n "$llm_model" ]] && _pc_smoke_ok "LITELLM_MODEL set (${llm_model})"
    fi

    if [[ -n "$ingest_back" ]]; then
        if [[ -f "$frontend_env" ]]; then
            ingest_front="$(_pc_env_get "$frontend_env" TSOC_INGEST_TOKEN)"
            if [[ "$ingest_front" == "$ingest_back" ]]; then
                _pc_smoke_ok "TSOC_INGEST_TOKEN matches backend and frontend"
            else
                _pc_smoke_fail "TSOC_INGEST_TOKEN mismatch between backend/.env and frontend/.env.local"
            fi
        fi
    fi

    echo ""
    if [[ $fail -eq 0 ]]; then
        if [[ $warn -eq 0 ]]; then
            ok "Verification passed: integration looks good (${pass}/${pass} checks)"
            echo ""
            info "Splunk may still need a restart for new apps — see reminder below."
        else
            ok "Verification passed with warnings: ${pass} OK, ${warn} warning(s) — review warnings above"
        fi
        return 0
    fi
    err "Verification failed: ${fail} check(s) failed, ${pass} passed, ${warn} warning(s)"
    err "Fix the failures above, then rerun: sudo bash $INSTALL_DIR/install/smoke-integration-config.sh"
    return 1
}
