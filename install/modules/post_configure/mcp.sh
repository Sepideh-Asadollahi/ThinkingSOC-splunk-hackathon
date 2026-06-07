#!/usr/bin/env bash
# Post-configure: Splunk MCP app install/RBAC on Splunk + auto-mint token into backend/.env.

_pc_splunk_rest_creds_available() {
    local env_file="$INSTALL_DIR/backend/.env"
    local user pass
    user="${PC_SPLUNK_USER:-}"
    pass="${PC_SPLUNK_PASS:-}"
    if [[ -z "$user" ]]; then
        user="$(_pc_env_get "$env_file" SPLUNK_USERNAME)"
    fi
    if [[ -z "$pass" ]]; then
        pass="$(_pc_env_get "$env_file" SPLUNK_PASSWORD)"
    fi
    [[ -n "$user" && -n "$pass" ]]
}

_pc_setup_splunk_mcp() {
    local venv_python="${VENV_PYTHON:-$INSTALL_DIR/backend/.venv/bin/python}"
    local script="${INSTALL_DIR}/scripts/setup_splunk_mcp.py"
    if [[ ! -f "$script" ]]; then
        warn "Splunk MCP setup script missing: $script"
        return 1
    fi
    if ! _pc_splunk_rest_creds_available; then
        info "Skipping Splunk MCP setup — no REST credentials in wizard or backend/.env"
        return 0
    fi

    info "Configuring Splunk MCP Server on Splunk (app 7931, RBAC, token) …"
    local -a cmd=("$venv_python" "$script" --env "$INSTALL_DIR/backend/.env")
    if [[ -n "${PC_SPLUNK_HOME:-}" ]]; then
        cmd+=(--splunk-home "$PC_SPLUNK_HOME")
    fi
    if [[ -n "${TSOC_SPLUNK_MCP_APP_PACKAGE:-}" ]]; then
        cmd+=(--app-package "$TSOC_SPLUNK_MCP_APP_PACKAGE")
    fi

    local out rc=0
    out="$("${cmd[@]}" 2>&1)" || rc=$?
    while IFS= read -r line; do
        case "$line" in
            OK:*)
                ok "${line#OK: }"
                ;;
            WARN:*)
                warn "${line#WARN: }"
                ;;
            ERROR:*)
                err "${line#ERROR: }"
                ;;
            *)
                [[ -n "$line" ]] && info "$line"
                ;;
        esac
    done <<<"$out"

    return "$rc"
}

_pc_mint_mcp_token() {
    local venv_python="${VENV_PYTHON:-$INSTALL_DIR/backend/.venv/bin/python}"
    local script="${INSTALL_DIR}/scripts/mint_splunk_mcp_token.py"
    local env_file="$INSTALL_DIR/backend/.env"
    if [[ ! -f "$script" ]]; then
        warn "MCP mint script missing: $script"
        return 1
    fi
    if ! _pc_splunk_rest_creds_available; then
        return 1
    fi
    info "Minting Splunk MCP bearer token into backend/.env …"
    if "$venv_python" "$script" --env "$env_file"; then
        ok "SPLUNK_MCP_TOKEN written to backend/.env (and SPLUNK_MCP_URL / MCP defaults)"
        return 0
    fi
    warn "MCP token mint failed — Splunk MCP Server app (7931) must be installed and enabled"
    warn "  After Splunk restart: $venv_python $script --env $env_file"
    return 1
}

# Full MCP path: Splunk app + RBAC via setup script, then ensure token exists (mint fallback).
_pc_ensure_mcp_token() {
    local env_file="$INSTALL_DIR/backend/.env"
    [[ -f "$env_file" ]] || return 1

    if ! _pc_splunk_rest_creds_available; then
        warn "MCP token not created — set SPLUNK_USERNAME and SPLUNK_PASSWORD in backend/.env first"
        return 0
    fi

    _pc_setup_splunk_mcp || true

    local existing_token
    existing_token="$(_pc_env_get "$env_file" SPLUNK_MCP_TOKEN)"

    existing_token="$(_pc_env_get "$env_file" SPLUNK_MCP_TOKEN)"
    if [[ -n "$existing_token" ]]; then
        ok "MCP bearer token ready in backend/.env"
        return 0
    fi

    warn "Setup did not write MCP token — retrying mint only …"
    _pc_mint_mcp_token
}
