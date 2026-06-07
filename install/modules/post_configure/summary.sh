#!/usr/bin/env bash
# Post-configure: print integration .env summary and Splunk restart reminder.

# Keys touched or set by post-install integration (backend/.env).
_PC_BACKEND_ENV_KEYS=(
    SPLUNK_HOME
    SPLUNK_MGMT_URL
    SPLUNK_USERNAME
    SPLUNK_PASSWORD
    SPLUNK_VERIFY_SSL
    LITELLM_MODEL
    LITELLM_API_KEY
    LITELLM_API_BASE
    TSOC_INGEST_TOKEN
    TSOC_INGEST_AUTO_ANALYZE
    TSOC_INGEST_AUTO_ANALYZE_PIPELINE
    TSOC_MCP_ENABLED
    SPLUNK_MCP_URL
    SPLUNK_MCP_TOKEN
    SPLUNK_MCP_VERIFY_SSL
    SPLUNK_MCP_TIMEOUT_SECONDS
    TSOC_SPL_USE_REST_PREDICT
    TSOC_MCP_SAIA_OPTIMIZE_SPL
    TSOC_MCP_SAIA_EXPLAIN_SPL
    TSOC_MCP_HUNTER_JUDGE_ENABLED
    TSOC_SPL_EXECUTE_VIA_MCP
    TSOC_SPL_LLM_REVIEW
    TSOC_EXECUTE_INVESTIGATION_SPL
)

_PC_FRONTEND_ENV_KEYS=(
    NEXT_PUBLIC_TSOC_SPLUNK_HOST
    NEXT_PUBLIC_TSOC_SPLUNK_PORT
    TSOC_INGEST_TOKEN
    TSOC_BACKEND_URL
    NEXT_PUBLIC_TSOC_APP_URL
)

_pc_env_key_is_secret() {
    local key="$1"
    case "$key" in
        *PASSWORD*|*SECRET*|*TOKEN*|*API_KEY*)
            return 0
            ;;
    esac
    return 1
}

_pc_format_env_display_value() {
    local key="$1" val="$2"
    if [[ -z "$val" ]]; then
        echo "(not set — add in file below)"
        return 0
    fi
    if _pc_env_key_is_secret "$key"; then
        if [[ "${#val}" -le 4 ]]; then
            echo "***"
        else
            echo "***${val: -4}  (${#val} chars — edit file to change)"
        fi
        return 0
    fi
    echo "$val"
}

_pc_print_env_file_summary() {
    local label="$1" path="$2"
    shift 2
    local -a keys=("$@")
    local key val display

    echo -e "  ${BOLD}${label}${NC}"
    echo -e "  ${CYAN}${path}${NC}"
    for key in "${keys[@]}"; do
        val="$(_pc_env_get "$path" "$key")"
        display="$(_pc_format_env_display_value "$key" "$val")"
        echo -e "    ${key}=${display}"
    done
    echo ""
}

_pc_print_post_install_env_summary() {
    local backend_env="${INSTALL_DIR}/backend/.env"
    local frontend_env="${INSTALL_DIR}/frontend/.env.local"

    step "Post-install environment variables (edit to customize)"
    echo ""
    echo "  Values below are read from disk after setup. Secrets are masked."
    echo "  Change any value in the files, then restart tsoc-backend and tsoc-frontend (and Splunk if needed)."
    echo ""

    if [[ -f "$backend_env" ]]; then
        _pc_print_env_file_summary "backend/.env" "$backend_env" "${_PC_BACKEND_ENV_KEYS[@]}"
    else
        warn "  backend/.env not found at ${backend_env}"
        echo ""
    fi

    if [[ -f "$frontend_env" ]]; then
        _pc_print_env_file_summary "frontend/.env.local" "$frontend_env" "${_PC_FRONTEND_ENV_KEYS[@]}"
    else
        warn "  frontend/.env.local not found at ${frontend_env}"
        echo ""
    fi
}

_pc_print_splunk_restart_reminder() {
    local splunk_home
    splunk_home="$(_pc_env_get "${INSTALL_DIR}/backend/.env" SPLUNK_HOME)"
    splunk_home="${splunk_home:-${PC_SPLUNK_HOME:-}}"

    echo ""
    echo -e "${YELLOW}${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}${BOLD}  Restart Splunk (required after app / MCP changes)${NC}"
    echo -e "${YELLOW}${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  ThinkingSOC_Hackathon and Splunk MCP Server (7931) only load fully"
    echo "  after a Splunk restart. Run as a user that can manage Splunk:"
    echo ""

    if [[ -n "$splunk_home" && -x "${splunk_home}/bin/splunk" ]]; then
        echo -e "    ${BOLD}${splunk_home}/bin/splunk restart${NC}"
    elif _pc_validate_splunk_home "${PC_SPLUNK_HOME:-/opt/splunk}"; then
        echo -e "    ${BOLD}${PC_SPLUNK_HOME}/bin/splunk restart${NC}"
    else
        echo -e "    ${BOLD}\$SPLUNK_HOME/bin/splunk restart${NC}"
        echo "    (set SPLUNK_HOME in backend/.env if your install path differs)"
    fi

    echo ""
    echo "  Verify apps:"
    echo "    \$SPLUNK_HOME/bin/splunk list app | grep -E 'ThinkingSOC_Hackathon|Splunk_MCP'"
    echo ""
}
