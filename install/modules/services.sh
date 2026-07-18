#!/usr/bin/env bash

# Printed by: install.sh --help (and referenced from install/README.md).
print_install_runtime_modes_help() {
    cat <<'EOF'

ThinkingSOC Lite — two ways to run backend + frontend after install
──────────────────────────────────────────────────────────────
Both use production UI: npm run build  →  npm run start  (not npm run dev)

  Backend API   http://127.0.0.1:9876     (localhost only)
  Frontend UI   http://<server-ip>:3000   (LAN / browser)
  Demo login    admin / 123456@a

During install.sh you choose:

  [1] WITH systemd (default, recommended)
      Units: tsoc-backend, tsoc-frontend — auto-start on boot
      Manage:
        sudo systemctl status|start|stop|restart tsoc-backend tsoc-frontend
        sudo journalctl -u tsoc-backend -f
        sudo journalctl -u tsoc-frontend -f

  [2] WITHOUT systemd (background)
      Logs: logs/backend.log, logs/frontend.log
      Manage:
        sudo bash scripts/start-tsoc-services.sh
        tail -f logs/backend.log logs/frontend.log

  Add systemd later (if you chose [2]):
        sudo bash scripts/install-systemd.sh

  Full guide: install/README.md  |  Project README: README.md

Default install directory: /opt/thinking-soc-splunk-hackathon
  Override: TSOC_INSTALL_DIR=/other/path sudo bash install.sh

Unattended install / smoke-test controls:
  NON_INTERACTIVE=true              use defaults without /dev/tty prompts
  TSOC_LOAD_DEMO_DATA=true|false    load the committed full demo bundle
  TSOC_SETUP_SYSTEMD=true|false     select systemd or background services
  TSOC_RESET_EXISTING_STACK=true    explicitly permit deletion of only the
                                    ThinkingSOC Lite containers/data volumes

TSOC_RESET_EXISTING_STACK is intentionally unset by default. Never enable it
on an existing deployment unless replacing its ThinkingSOC Lite database is intended.

EOF
}

_tsoc_tcp_port_in_use() {
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
        ss -tln 2>/dev/null | grep -qE ":${port}([[:space:]]|$)"
        return $?
    fi
    if command -v netstat >/dev/null 2>&1; then
        netstat -tln 2>/dev/null | grep -qE ":${port}([[:space:]]|$)"
        return $?
    fi
    return 1
}

ensure_frontend_production_build() {
    local frontend_dir="$INSTALL_DIR/frontend"
    local force="${1:-false}"
    if [[ ! -d "$frontend_dir/node_modules" ]]; then
        err "Frontend node_modules missing — run: cd frontend && npm install"
        return 1
    fi
    if [[ "$force" != true && -f "$frontend_dir/.next/BUILD_ID" ]]; then
        ok "Frontend production build present (.next/BUILD_ID)"
        return 0
    fi
    info "Building frontend for production (npm run build) …"
    (
        cd "$frontend_dir"
        if [[ "${INSTALL_VERBOSE:-false}" == true ]]; then
            run_cmd npm run build
        else
            npm run build
        fi
    ) || return 1
    ok "Frontend production build complete"
}

# Avoid HTTP_PROXY breaking localhost checks during install.
_tsoc_curl_ok() {
    curl -sf --noproxy '*' "$@" &>/dev/null
}

_wait_for_http() {
    local url="$1"
    local label="$2"
    local attempts="${3:-30}"
    local delay="${4:-2}"
    local i
    for (( i = 1; i <= attempts; i++ )); do
        if _tsoc_curl_ok "$url"; then
            ok "${label} ready (${url})"
            return 0
        fi
        sleep "$delay"
    done
    warn "${label} not responding yet at ${url}"
    return 1
}

_wait_for_backend_service() {
    if declare -F _wait_for_backend_with_embedding_notice >/dev/null 2>&1; then
        _wait_for_backend_with_embedding_notice "$@"
        return $?
    fi
    # Standalone helpers such as scripts/start-tsoc-services.sh source this
    # module without embedding.sh. Keep those commands self-contained.
    _wait_for_http "$@"
}

_backend_startup_diagnose() {
    warn "Backend /health not ready yet — common causes:"
    info "  · First start loads the embedding model into RAM (~1–3 min even after download)"
    info "  · Check logs: sudo journalctl -u tsoc-backend -n 80 --no-pager"
    info "  · Or: tail -80 ${INSTALL_DIR}/logs/backend.log 2>/dev/null"
    if systemctl is-active --quiet tsoc-backend 2>/dev/null; then
        info "  · Service is active — wait and retry: curl -s http://127.0.0.1:9876/health"
    else
        err "  · tsoc-backend is not active: sudo systemctl status tsoc-backend"
    fi
}

start_application_services() {
    local venv_python="${VENV_PYTHON:-$INSTALL_DIR/backend/.venv/bin/python}"
    local log_dir="${INSTALL_DIR}/logs"
    mkdir -p "$log_dir"

    if [[ ! -x "$venv_python" ]]; then
        err "Backend venv missing: $venv_python"
        return 1
    fi

    if _tsoc_tcp_port_in_use 9876; then
        if _tsoc_curl_ok "http://127.0.0.1:9876/health"; then
            ok "Backend already listening on port 9876 and healthy"
        else
            err "Port 9876 is occupied but GET /health failed; refusing to treat it as ThinkingSOC Lite"
            return 1
        fi
    else
        info "Starting backend API (log: ${log_dir}/backend.log) …"
        (
            cd "$INSTALL_DIR/backend"
            nohup setsid "$venv_python" run.py >>"${log_dir}/backend.log" 2>&1 &
            echo $! >"${log_dir}/backend.pid"
        )
        _wait_for_backend_service "http://127.0.0.1:9876/health" "Backend API" 300 2 || true
    fi

    if _tsoc_tcp_port_in_use 3000; then
        if _tsoc_curl_ok "http://127.0.0.1:3000/login"; then
            ok "Frontend already listening on port 3000 and reachable"
        else
            err "Port 3000 is occupied but GET /login failed; refusing to treat it as ThinkingSOC Lite"
            return 1
        fi
    else
        ensure_frontend_production_build || return 1
        info "Starting frontend UI — production (npm run start, log: ${log_dir}/frontend.log) …"
        (
            cd "$INSTALL_DIR/frontend"
            export NODE_ENV=production
            nohup setsid npm run start >>"${log_dir}/frontend.log" 2>&1 &
            echo $! >"${log_dir}/frontend.pid"
        )
        _wait_for_http "http://127.0.0.1:3000/login" "Frontend UI" 60 2 || true
    fi

    ok "Application services started (backend :9876, frontend :3000 production)"
    info "  Logs: tail -f ${log_dir}/backend.log ${log_dir}/frontend.log"
    return 0
}

restart_application_services() {
    info "Restarting background backend + frontend to apply configuration …"
    stop_application_services
    sleep 2
    start_application_services
}

stop_application_services() {
    local log_dir="${INSTALL_DIR}/logs"
    local pid_file name
    for name in backend frontend; do
        pid_file="${log_dir}/${name}.pid"
        if [[ -f "$pid_file" ]]; then
            local pid
            pid="$(cat "$pid_file" 2>/dev/null || true)"
            if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
                # New installs run each service in its own process group so npm
                # and its next-server child stop together. The direct-PID
                # fallback keeps compatibility with older pid files.
                kill -TERM -- "-${pid}" 2>/dev/null || kill "$pid" 2>/dev/null || true
                ok "Stopped ${name} (pid ${pid})"
            fi
            rm -f "$pid_file"
        fi
    done

    # Recover safely from stale/missing pid files: stop only listeners whose
    # working directory belongs to this exact checkout. Never kill an unrelated
    # process merely because it owns one of the expected ports.
    local spec service port pid cwd
    for spec in "backend:9876" "frontend:3000"; do
        service="${spec%%:*}"
        port="${spec##*:}"
        while read -r pid; do
            [[ "$pid" =~ ^[0-9]+$ ]] || continue
            kill -0 "$pid" 2>/dev/null || continue
            cwd="$(readlink -f "/proc/${pid}/cwd" 2>/dev/null || true)"
            if [[ "$cwd" == "$INSTALL_DIR" || "$cwd" == "$INSTALL_DIR/"* ]]; then
                kill "$pid" 2>/dev/null || true
                ok "Stopped unmanaged ${service} listener from this checkout (pid ${pid})"
            else
                warn "Did not stop pid ${pid} on port ${port}; cwd is outside ${INSTALL_DIR}"
            fi
        done < <(ss -ltnpH 2>/dev/null \
            | grep -E ":${port}([[:space:]]|$)" \
            | grep -oE 'pid=[0-9]+' \
            | cut -d= -f2 \
            | sort -u || true)
    done

    local i
    for ((i = 1; i <= 20; i++)); do
        if ! _tsoc_tcp_port_in_use 9876 && ! _tsoc_tcp_port_in_use 3000; then
            return 0
        fi
        sleep 0.25
    done
}

create_systemd_services() {
    local venv_python="$INSTALL_DIR/backend/.venv/bin/python"

    cat > /etc/systemd/system/tsoc-backend.service <<EOF
[Unit]
Description=ThinkingSOC Lite Backend (FastAPI)
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR/backend
ExecStart=$venv_python run.py
Restart=on-failure
RestartSec=5
Environment=TSOC_HTTP_HOST=127.0.0.1
Environment=TSOC_HTTP_PORT=9876

[Install]
WantedBy=multi-user.target
EOF

    local node_path
    node_path="$(command -v node)"
    local next_bin="$INSTALL_DIR/frontend/node_modules/.bin/next"

    cat > /etc/systemd/system/tsoc-frontend.service <<EOF
[Unit]
Description=ThinkingSOC Lite Frontend (Next.js)
After=network.target tsoc-backend.service

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR/frontend
ExecStart=${node_path} ${next_bin} start -H 0.0.0.0 -p 3000
Restart=on-failure
RestartSec=5
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF

    run_cmd systemctl daemon-reload
    run_cmd systemctl enable tsoc-backend.service
    run_cmd systemctl enable tsoc-frontend.service
    run_cmd systemctl start tsoc-backend.service
    run_cmd systemctl start tsoc-frontend.service

    info "Starting backend — /health should respond within ~1–3 min (RAG loads in background) …"
    if ! _wait_for_backend_service "http://127.0.0.1:9876/health" "Backend API" 180 2; then
        _backend_startup_diagnose
    fi
    _wait_for_http "http://127.0.0.1:3000/login" "Frontend UI" 60 2 || true

    ok "Systemd services created and started"
    info "  tsoc-backend  → port 9876"
    info "  tsoc-frontend → port 3000"
}

# Printed at end of install.sh when services run without systemd (see README).
print_production_services_help() {
    echo -e "  ${BOLD}Mode:${NC}           production (npm run start — not npm run dev)"
    echo -e "  ${BOLD}Backend API:${NC}    http://127.0.0.1:9876  (log: logs/backend.log)"
    echo -e "  ${BOLD}Frontend UI:${NC}    http://${SERVER_IP:-127.0.0.1}:3000  (log: logs/frontend.log)"
    echo ""
    echo -e "  ${BOLD}Status${NC}"
    echo "    ss -tln | grep -E ':9876|:3000'"
    echo "    curl -s http://127.0.0.1:9876/health"
    echo "    curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:3000/login"
    echo ""
    echo -e "  ${BOLD}Restart stack${NC}"
    echo "    sudo bash $INSTALL_DIR/scripts/start-tsoc-services.sh"
    echo ""
    echo -e "  ${BOLD}Stop stack${NC}"
    echo "    # PIDs in logs/backend.pid and logs/frontend.pid"
    echo "    kill \$(cat $INSTALL_DIR/logs/frontend.pid) \$(cat $INSTALL_DIR/logs/backend.pid) 2>/dev/null || true"
    echo ""
    echo -e "  ${BOLD}Logs (live)${NC}"
    echo "    tail -f $INSTALL_DIR/logs/backend.log"
    echo "    tail -f $INSTALL_DIR/logs/frontend.log"
    echo ""
    echo -e "  ${BOLD}After UI code changes${NC}"
    echo "    cd $INSTALL_DIR/frontend && npm run build"
    echo "    sudo bash $INSTALL_DIR/scripts/start-tsoc-services.sh"
    echo ""
    echo -e "  ${BOLD}Switch to systemd (auto-start on boot)${NC}"
    echo "    sudo bash $INSTALL_DIR/scripts/install-systemd.sh"
}

# Printed at end of install.sh when systemd units are installed (also documented in README).
print_systemd_control_help() {
    echo -e "  ${BOLD}Systemd units:${NC}  tsoc-backend (API :9876)  ·  tsoc-frontend (UI :3000)"
    echo -e "  ${BOLD}Requires:${NC}       Docker running (Postgres / Qdrant / Neo4j containers)"
    echo ""
    echo -e "  ${BOLD}Status & health${NC}"
    echo "    sudo systemctl status tsoc-backend tsoc-frontend"
    echo "    curl -s http://127.0.0.1:9876/health"
    echo "    curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:3000/login"
    echo ""
    echo -e "  ${BOLD}Start / stop / restart${NC}"
    echo "    sudo systemctl start tsoc-backend tsoc-frontend"
    echo "    sudo systemctl stop tsoc-frontend tsoc-backend    # UI first, then API"
    echo "    sudo systemctl restart tsoc-backend tsoc-frontend"
    echo ""
    echo -e "  ${BOLD}Boot (auto-start)${NC}"
    echo "    sudo systemctl enable tsoc-backend tsoc-frontend   # on"
    echo "    sudo systemctl disable tsoc-backend tsoc-frontend # off"
    echo ""
    echo -e "  ${BOLD}Logs (live)${NC}"
    echo "    sudo journalctl -u tsoc-backend -f"
    echo "    sudo journalctl -u tsoc-frontend -f"
    echo "    sudo journalctl -u tsoc-backend -u tsoc-frontend -f"
    echo ""
    echo -e "  ${BOLD}Logs (recent)${NC}"
    echo "    sudo journalctl -u tsoc-backend -n 100 --no-pager"
    echo "    sudo journalctl -u tsoc-frontend -n 100 --no-pager"
    echo ""
    echo -e "  ${BOLD}After editing unit files${NC}"
    echo "    sudo systemctl daemon-reload"
    echo "    sudo systemctl restart tsoc-backend tsoc-frontend"
    echo ""
    echo -e "  ${BOLD}Unit files:${NC}"
    echo "    /etc/systemd/system/tsoc-backend.service"
    echo "    /etc/systemd/system/tsoc-frontend.service"
    echo ""
    echo -e "  ${BOLD}Frontend rebuild (production UI):${NC}"
    echo "    cd $INSTALL_DIR/frontend && npm run build"
    echo "    sudo systemctl restart tsoc-frontend"
}
