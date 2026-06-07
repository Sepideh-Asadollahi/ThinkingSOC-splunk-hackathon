#!/usr/bin/env bash
# Post-configure: write integration settings to backend/.env and frontend/.env.local.

_pc_apply_backend_env() {
    local env_file="$INSTALL_DIR/backend/.env"
    [[ -f "$env_file" ]] || { err "backend/.env missing"; return 1; }

    if [[ -n "${PC_SPLUNK_HOME:-}" ]]; then
        _upsert_env_line "$env_file" "SPLUNK_HOME" "$PC_SPLUNK_HOME"
    fi
    if [[ -n "${PC_SPLUNK_MGMT_URL:-}" ]]; then
        _upsert_env_line "$env_file" "SPLUNK_MGMT_URL" "$PC_SPLUNK_MGMT_URL"
    fi
    if [[ -n "${PC_SPLUNK_USER:-}" ]]; then
        _upsert_env_line "$env_file" "SPLUNK_USERNAME" "$PC_SPLUNK_USER"
    fi
    if [[ -n "${PC_SPLUNK_PASS:-}" ]]; then
        _upsert_env_line "$env_file" "SPLUNK_PASSWORD" "$PC_SPLUNK_PASS"
    fi
    [[ -n "${PC_LITELLM_MODEL:-}" ]] && _upsert_env_line "$env_file" "LITELLM_MODEL" "$PC_LITELLM_MODEL"
    [[ -n "${PC_LITELLM_KEY:-}" ]] && _upsert_env_line "$env_file" "LITELLM_API_KEY" "$PC_LITELLM_KEY"
    [[ -n "${PC_LITELLM_API_BASE:-}" ]] && _upsert_env_line "$env_file" "LITELLM_API_BASE" "$PC_LITELLM_API_BASE"
    if [[ -n "${PC_INGEST_TOKEN:-}" ]]; then
        _upsert_env_line "$env_file" "TSOC_INGEST_TOKEN" "$PC_INGEST_TOKEN"
    fi

    _upsert_env_line "$env_file" "TSOC_MCP_ENABLED" "true"
    _ensure_ingest_auto_analyze_env "$env_file" false
    ok "Updated backend/.env"
}

_pc_apply_frontend_env() {
    local env_file="$INSTALL_DIR/frontend/.env.local"
    [[ -f "$env_file" ]] || return 0

    if [[ -n "${PC_SPLUNK_MGMT_URL:-}" ]]; then
        _pc_parse_mgmt_url "$PC_SPLUNK_MGMT_URL"
        _upsert_env_line "$env_file" "NEXT_PUBLIC_TSOC_SPLUNK_HOST" "$_PC_SPLUNK_HOST"
        _upsert_env_line "$env_file" "NEXT_PUBLIC_TSOC_SPLUNK_PORT" "$_PC_SPLUNK_PORT"
    fi
    _pc_sync_ingest_token_to_frontend
    ok "Updated frontend/.env.local (Splunk UI hints + ingest token if set)"
}

# Keep frontend proxy token aligned with backend (fixes 401 on dashboard and other UI routes).
_pc_sync_ingest_token_to_frontend() {
    local backend_env="$INSTALL_DIR/backend/.env"
    local frontend_env="$INSTALL_DIR/frontend/.env.local"
    [[ -f "$frontend_env" ]] || return 0

    local tok="${PC_INGEST_TOKEN:-}"
    if [[ -z "$tok" ]]; then
        tok="$(_pc_env_get "$backend_env" TSOC_INGEST_TOKEN)"
    fi
    if [[ -n "$tok" ]]; then
        _upsert_env_line "$frontend_env" "TSOC_INGEST_TOKEN" "$tok"
    fi
}
