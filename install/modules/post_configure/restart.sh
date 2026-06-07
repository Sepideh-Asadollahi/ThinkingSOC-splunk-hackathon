#!/usr/bin/env bash
# Post-configure: restart tsoc-backend + tsoc-frontend after .env changes.

_pc_tsoc_uses_systemd() {
    [[ "${SETUP_SYSTEMD:-false}" == true ]] \
        && [[ -f /etc/systemd/system/tsoc-backend.service ]] \
        && systemctl is-enabled tsoc-backend &>/dev/null
}

_pc_print_manual_tsoc_restart_instructions() {
    local ui_host="${SERVER_IP:-127.0.0.1}"
    echo ""
    err "Restart ThinkingSOC manually so backend/.env and frontend/.env.local take effect."
    echo ""
    if _pc_tsoc_uses_systemd; then
        echo -e "  ${BOLD}With systemd:${NC}"
        echo "    sudo systemctl restart tsoc-backend tsoc-frontend"
        echo "    sudo systemctl status tsoc-backend tsoc-frontend"
        echo "    sudo journalctl -u tsoc-backend -u tsoc-frontend -n 80 --no-pager"
    else
        echo -e "  ${BOLD}Without systemd (background processes):${NC}"
        echo "    sudo bash ${INSTALL_DIR}/scripts/start-tsoc-services.sh"
        echo "    tail -f ${INSTALL_DIR}/logs/backend.log ${INSTALL_DIR}/logs/frontend.log"
    fi
    echo ""
    echo "  Hard-refresh the browser (Ctrl+Shift+R), then open:"
    echo "    http://${ui_host}:3000/splunk-connection"
    echo ""
    echo "  If you see \"Missing Authorization bearer token\", TSOC_INGEST_TOKEN must match in"
    echo "  backend/.env and frontend/.env.local — then restart tsoc-frontend again."
    echo ""
}

_pc_verify_tsoc_services_running() {
    if _pc_tsoc_uses_systemd; then
        if ! systemctl is-active --quiet tsoc-backend 2>/dev/null; then
            warn "tsoc-backend is not active after restart"
            return 1
        fi
        if ! systemctl is-active --quiet tsoc-frontend 2>/dev/null; then
            warn "tsoc-frontend is not active after restart"
            return 1
        fi
    else
        if ! _tsoc_tcp_port_in_use 9876 2>/dev/null; then
            warn "Backend not listening on port 9876 after restart"
            return 1
        fi
        if ! _tsoc_tcp_port_in_use 3000 2>/dev/null; then
            warn "Frontend not listening on port 3000 after restart"
            return 1
        fi
    fi

    if ! _tsoc_curl_ok "http://127.0.0.1:9876/health"; then
        warn "Backend /health not ready after restart (embedding model may still be loading)"
        return 1
    fi
    if ! _tsoc_curl_ok -o /dev/null "http://127.0.0.1:3000/login"; then
        warn "Frontend /login not reachable after restart"
        return 1
    fi
    ok "Backend (:9876) and frontend (:3000) are running after restart"
    return 0
}

# Restart both services so backend/.env and frontend/.env.local are loaded (ingest token, Splunk, MCP).
_pc_restart_tsoc_services_for_env() {
    local backend_ok=false frontend_ok=false

    if _pc_tsoc_uses_systemd; then
        info "Restarting tsoc-backend and tsoc-frontend (systemd) …"
        if run_cmd systemctl restart tsoc-backend.service; then
            backend_ok=true
        else
            warn "systemctl restart tsoc-backend failed"
        fi
        if run_cmd systemctl restart tsoc-frontend.service; then
            frontend_ok=true
        else
            warn "systemctl restart tsoc-frontend failed"
        fi
        if [[ "$backend_ok" != true || "$frontend_ok" != true ]]; then
            return 1
        fi
        _wait_for_backend_with_embedding_notice "http://127.0.0.1:9876/health" "Backend API" 180 2 || true
        _wait_for_http "http://127.0.0.1:3000/login" "Frontend UI" 60 2 || true
    else
        if restart_application_services; then
            backend_ok=true
            frontend_ok=true
        else
            warn "restart_application_services failed"
            return 1
        fi
    fi

    _pc_verify_tsoc_services_running
}

# Backward-compatible alias (older modules called backend-only restart).
_pc_restart_backend_for_env() {
    _pc_restart_tsoc_services_for_env
}
