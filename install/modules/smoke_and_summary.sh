#!/usr/bin/env bash

run_smoke_test() {
    local pass=0 fail=0

    smoke_ok() { ok "  $1"; pass=$((pass + 1)); }
    smoke_fail() { err " $1"; fail=$((fail + 1)); }

    [[ -f "$INSTALL_DIR/setup.py" ]] && smoke_ok "Repository files present" || smoke_fail "Repository files missing"
    [[ -f "$INSTALL_DIR/backend/.venv/bin/python" ]] && smoke_ok "Python virtual environment" || smoke_fail "Python virtual environment missing"
    [[ -f "$INSTALL_DIR/backend/.env" ]] && smoke_ok "backend/.env config" || smoke_fail "backend/.env missing"
    [[ -f "$INSTALL_DIR/frontend/.env.local" ]] && smoke_ok "frontend/.env.local config" || smoke_fail "frontend/.env.local missing"
    [[ -d "$INSTALL_DIR/frontend/node_modules" ]] && smoke_ok "Frontend node_modules" || smoke_fail "Frontend node_modules missing"

    if "$INSTALL_DIR/backend/.venv/bin/python" -c "import fastapi, uvicorn, asyncpg, litellm" 2>/dev/null; then
        smoke_ok "Key Python packages importable (fastapi, uvicorn, asyncpg, litellm)"
    else
        smoke_fail "Some Python packages failed to import"
    fi

    local containers=("tsoc-postgres" "tsoc-qdrant" "tsoc-neo4j")
    for cname in "${containers[@]}"; do
        if docker ps --filter "name=^${cname}$" --filter "status=running" -q 2>/dev/null | grep -q .; then
            smoke_ok "Docker container: ${cname} running"
        else
            smoke_fail "Docker container: ${cname} NOT running"
        fi
    done

    if docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
        smoke_ok "PostgreSQL accepting connections"
    else
        smoke_fail "PostgreSQL not responding"
    fi

    if curl -sf --noproxy '*' http://127.0.0.1:6333/readyz &>/dev/null; then
        smoke_ok "Qdrant HTTP ready"
    else
        smoke_fail "Qdrant not responding on port 6333"
    fi

    if curl -sf --noproxy '*' http://127.0.0.1:7474 &>/dev/null; then
        smoke_ok "Neo4j HTTP ready"
    else
        smoke_fail "Neo4j not responding on port 7474"
    fi

    local tables
    tables="$(docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc \
        "SELECT string_agg(table_name, ',') FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';" 2>/dev/null || echo "")"
    if [[ "$tables" == *"tsoc_records"* && "$tables" == *"tsoc_users"* ]]; then
        smoke_ok "Database schema applied (tsoc_records, tsoc_users found)"
    else
        smoke_fail "Database schema missing or incomplete"
    fi

    if [[ "$LOAD_DEMO_DATA" == true ]]; then
        local user_count asset_count rel_count
        user_count="$(docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc "SELECT COUNT(*) FROM tsoc_users;" 2>/dev/null || echo "0")"
        asset_count="$(docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc "SELECT COUNT(*) FROM tsoc_assets;" 2>/dev/null || echo "0")"
        rel_count="$(docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc "SELECT COUNT(*) FROM tsoc_relationships;" 2>/dev/null || echo "0")"
        # Full demo = root + scenario packs (botsv1, attacks, observability); expect 7 users / 7 assets.
        local record_count identity_count finding_count
        record_count="$(docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc "SELECT COUNT(*) FROM tsoc_records;" 2>/dev/null || echo "0")"
        identity_count="$(docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc "SELECT COUNT(*) FROM tsoc_identity_rules;" 2>/dev/null || echo "0")"
        finding_count="$(docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc "SELECT COUNT(*) FROM graph_findings;" 2>/dev/null || echo "0")"
        if [[ "$user_count" -ge 7 && "$asset_count" -ge 7 && "$rel_count" -ge 8 && "$record_count" -ge 1 && "$identity_count" -ge 1 && "$finding_count" -ge 1 ]] 2>/dev/null; then
            smoke_ok "Demo moment loaded (${user_count} users, ${asset_count} assets, ${rel_count} relationships, ${identity_count} identity rules, ${record_count} latest records, ${finding_count} correlation finding)"
        elif [[ "$user_count" -ge 7 && "$asset_count" -ge 7 && "$rel_count" -ge 8 ]] 2>/dev/null; then
            smoke_ok "Demo inventory loaded (${user_count} users, ${asset_count} assets, ${rel_count} relationships; records=${record_count})"
        elif [[ "$user_count" -gt 0 ]] 2>/dev/null; then
            smoke_fail "Demo data incomplete (${user_count} users, ${asset_count} assets, ${rel_count} relationships; expected ≥7/≥7/≥8)"
        else
            smoke_fail "Demo data not loaded (tsoc_users is empty)"
        fi
    fi

    if [[ "$SETUP_SYSTEMD" == true ]]; then
        for svc in tsoc-backend tsoc-frontend; do
            if systemctl is-active --quiet "$svc" 2>/dev/null; then
                smoke_ok "Systemd service: ${svc} active"
            else
                smoke_fail "Systemd service: ${svc} NOT active"
            fi
        done
    elif _tsoc_tcp_port_in_use 9876 2>/dev/null || _tsoc_tcp_port_in_use 3000 2>/dev/null; then
        smoke_ok "Application services started by installer (non-systemd)"
    else
        smoke_fail "Backend and frontend are not running (installer should have started them)"
    fi

    if curl -sf --noproxy '*' http://127.0.0.1:9876/health &>/dev/null; then
        smoke_ok "Backend API health check (GET /health)"
    elif [[ "$SETUP_SYSTEMD" == true ]] && systemctl is-active --quiet tsoc-backend 2>/dev/null; then
        echo ""
        info "Smoke test: tsoc-backend is active but /health not ready — waiting up to ~6 min …"
        if _wait_for_backend_with_embedding_notice "http://127.0.0.1:9876/health" "Backend API" 180 2; then
            smoke_ok "Backend API health check (GET /health, after wait)"
        else
            smoke_fail "Backend API not responding on http://127.0.0.1:9876/health"
            _backend_startup_diagnose
        fi
    elif _tsoc_tcp_port_in_use 9876 2>/dev/null; then
        info "Smoke test: port 9876 open — waiting for /health …"
        if _wait_for_backend_with_embedding_notice "http://127.0.0.1:9876/health" "Backend API" 180 2; then
            smoke_ok "Backend API health check (GET /health, after wait)"
        else
            smoke_fail "Backend API not responding on http://127.0.0.1:9876/health"
            _backend_startup_diagnose
        fi
    else
        smoke_fail "Backend API not responding on http://127.0.0.1:9876/health"
        _backend_startup_diagnose
    fi

    if curl -sf --noproxy '*' -o /dev/null http://127.0.0.1:3000/login &>/dev/null; then
        smoke_ok "Frontend UI reachable (GET /login)"
    else
        smoke_fail "Frontend UI not responding on http://127.0.0.1:3000/login"
    fi

    echo ""
    if [[ $fail -eq 0 ]]; then
        ok "Smoke test passed: ${pass}/${pass} checks OK"
        return 0
    fi
    warn "Smoke test: ${pass} passed, ${fail} failed"
    return 1
}

print_summary() {
    echo ""
    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  ThinkingSOC installed successfully!${NC}"
    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BOLD}Install directory:${NC}  $INSTALL_DIR"
    echo -e "  ${BOLD}Backend API:${NC}        http://127.0.0.1:9876  (localhost only)"
    echo -e "  ${BOLD}Frontend UI:${NC}        http://${SERVER_IP}:3000  (accessible from network)"
    echo -e "  ${BOLD}Demo login:${NC}         admin / 123456@a"
    if [[ "${LOAD_DEMO_DATA:-false}" == true ]]; then
        echo -e "  ${BOLD}Demo data:${NC}          full database backup restored if you chose load during install"
        if [[ -n "${DEMO_RESTORE_LOG:-}" && -f "${DEMO_RESTORE_LOG}" ]]; then
            echo -e "  ${BOLD}Demo restore log:${NC}   ${DEMO_RESTORE_LOG}"
        else
            echo -e "  ${BOLD}Demo restore log:${NC}   ${INSTALL_DIR}/logs/demo-restore.log"
        fi
    fi
    echo ""

    if [[ "$SETUP_SYSTEMD" == true ]]; then
        echo -e "  ${CYAN}${BOLD}── Service control (systemd) ──${NC}"
        echo ""
        print_systemd_control_help
    else
        echo -e "  ${CYAN}${BOLD}── Service control (background / production) ──${NC}"
        echo ""
        print_production_services_help
    fi

    echo ""
    echo -e "  ${BOLD}Note:${NC} Login is handled by the frontend (admin / 123456@a)."
    echo "    Use npm run dev only for local UI development (see README Quick start)."
    echo ""
    echo -e "  ${BOLD}Splunk / LiteLLM / MCP:${NC} Optional wizard runs next (or later):"
    echo "    sudo bash $INSTALL_DIR/scripts/configure-integration.sh"

    echo ""
}
