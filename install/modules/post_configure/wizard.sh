#!/usr/bin/env bash
# Post-configure: interactive integration wizard (Splunk, LiteLLM, MCP).

run_post_install_configure() {
    if [[ "$NON_INTERACTIVE" == "true" ]]; then
        info "NON_INTERACTIVE=true — skipping post-install integration wizard"
        info "Run later: sudo bash $INSTALL_DIR/scripts/configure-integration.sh"
        return 0
    fi

    echo ""
    step "Post-install integration setup (optional)"
    echo ""
    echo "  Configure minimum integrations now:"
    echo "    · Splunk install path (SPLUNK_HOME) + REST credentials"
    echo "    · Copy ThinkingSOC_Hackathon into Splunk"
    echo "    · LiteLLM: LITELLM_MODEL + LITELLM_API_KEY (required for SOC analysis)"
    echo "    · Splunk MCP Server app (7931), RBAC, and bearer token on Splunk"
    echo ""
    echo "  You can skip and run this wizard anytime:"
    echo "    sudo bash $INSTALL_DIR/scripts/configure-integration.sh"
    echo ""

    if ! prompt_yn "Run integration setup wizard now?" "y"; then
        info "Skipped — edit backend/.env manually or run configure-integration.sh later"
        if prompt_yn "Run live verification (smoke test) on current config?" "n"; then
            run_integration_configure_smoke || true
        fi
        return 0
    fi

    local default_home splunk_home mgmt_url splunk_user splunk_pass
    default_home="$(_pc_default_splunk_home)"

    echo ""
    echo -e "  ${BOLD}Splunk install path${NC} (used for SAIA repair and app install)"
    splunk_home="$(prompt_input "SPLUNK_HOME [${default_home}]:" "$default_home")"
    splunk_home="${splunk_home:-$default_home}"
    PC_SPLUNK_HOME="$splunk_home"

    if _pc_validate_splunk_home "$splunk_home"; then
        ok "Found Splunk binary at ${splunk_home}/bin/splunk"
    else
        warn "Splunk binary not found at ${splunk_home}/bin/splunk — app install and restart will be skipped"
    fi

    echo ""
    mgmt_url="$(prompt_input "Splunk management URL (REST) [https://127.0.0.1:8089]:" "https://127.0.0.1:8089")"
    PC_SPLUNK_MGMT_URL="${mgmt_url:-https://127.0.0.1:8089}"

    echo ""
    splunk_user="$(prompt_input "Splunk REST username (service account):" "")"
    if [[ -z "$splunk_user" ]]; then
        warn "No Splunk username — REST/MCP steps will be skipped"
        PC_SPLUNK_USER=""
        PC_SPLUNK_PASS=""
    else
        PC_SPLUNK_USER="$splunk_user"
        splunk_pass="$(prompt_secret "Splunk REST password:")"
        PC_SPLUNK_PASS="$splunk_pass"
    fi

    if _pc_validate_splunk_home "$splunk_home" && [[ -d "${INSTALL_DIR}/ThinkingSOC_Hackathon" ]]; then
        echo ""
        if prompt_yn "Install ThinkingSOC_Hackathon into \$SPLUNK_HOME/etc/apps?" "y"; then
            _pc_install_thinking_soc_app "$splunk_home" || true
        fi
    fi

    echo ""
    step "LLM setup (LiteLLM) — required"
    echo "  SOC analysis (Defender / Hunter / Judge) uses LiteLLM plus rule-based fallbacks when the model fails."
    echo ""
    PC_LITELLM_KEY=""
    PC_LITELLM_API_BASE=""
    _pc_prompt_litellm_config

    PC_INGEST_TOKEN=""
    echo ""
    if prompt_yn "Set a shared webhook ingest token (backend + frontend)?" "n"; then
        PC_INGEST_TOKEN="$(openssl rand -hex 24)"
        ok "Generated TSOC_INGEST_TOKEN (saved to backend/.env and frontend/.env.local)"
    fi

    _pc_apply_backend_env || return 1
    _pc_apply_frontend_env

    echo ""
    step "Splunk MCP token (automatic)"
    info "Installs/enables Splunk MCP Server (7931), grants mcp_tool_execute, mints SPLUNK_MCP_TOKEN."
    _pc_ensure_mcp_token || true

    echo ""
    step "Reload ThinkingSOC services"
    info "Restarting backend and frontend (required so .env / .env.local — e.g. TSOC_INGEST_TOKEN — load in the UI proxy) …"
    if ! _pc_restart_tsoc_services_for_env; then
        warn "Automatic restart did not complete successfully"
        _pc_print_manual_tsoc_restart_instructions
    fi

    echo ""
    ok "Configuration written — running live verification …"
    echo ""

    if run_integration_configure_smoke; then
        ok "Post-install integration verified (smoke test passed)"
    else
        warn "Smoke test reported problems — fix them before demo; config files are still listed below"
    fi

    _pc_print_post_install_env_summary
    _pc_print_splunk_restart_reminder

    echo -e "  ${BOLD}Next steps (Splunk UI):${NC}"
    echo "    · Webhook alert action → http://127.0.0.1:9876/api/v1/alerts/splunk-ingest"
    echo "    · Auto ingestion is on by default (TSOC_INGEST_AUTO_ANALYZE=true in backend/.env)"
    local ingest_hint
    ingest_hint="$(_pc_env_get "${INSTALL_DIR}/backend/.env" TSOC_INGEST_TOKEN)"
    if [[ -n "$ingest_hint" ]]; then
        echo "    · Add header: Authorization: Bearer <TSOC_INGEST_TOKEN from backend/.env>"
    fi
    echo "    · Docs: docs/15-splunk-mcp-integration.md  |  README.md § Splunk-side setup"
    echo ""
    echo -e "  ${BOLD}Re-run verification:${NC} sudo bash $INSTALL_DIR/install/smoke-integration-config.sh"
    echo ""
}
