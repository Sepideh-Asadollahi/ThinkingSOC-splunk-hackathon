#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# ThinkingSOC — Installer Entrypoint
# ──────────────────────────────────────────────────────────────────────────────
#
# RUN:  cd /opt/thinking-soc-splunk-hackathon && sudo bash install.sh
#       curl -fsSL …/install/bootstrap.sh | sudo bash   (one-liner; use bootstrap.sh, not install.sh)
# HELP: sudo bash install.sh --help
#
# Default install directory: /opt/thinking-soc-splunk-hackathon (override: TSOC_INSTALL_DIR)
#
# After install, backend + frontend run in ONE of two modes (you choose during
# install). Both use production frontend: npm run build && npm run start.
#
#   MODE A — WITH systemd (default, recommended for demo servers)
#     Units: tsoc-backend (:9876)  tsoc-frontend (:3000)
#     Auto-start on boot. Manage:
#       systemctl status|start|stop|restart tsoc-backend tsoc-frontend
#       journalctl -u tsoc-backend -f
#
#   MODE B — WITHOUT systemd (background processes)
#     Logs: logs/backend.log  logs/frontend.log
#     Manage:
#       sudo bash scripts/start-tsoc-services.sh
#       tail -f logs/backend.log logs/frontend.log
#     Enable systemd later: sudo bash scripts/install-systemd.sh
#
# Full operator guide: install/README.md
# Project documentation: README.md (sections "Service control with systemd" and
# "Production services (no systemd)")
#
# ──────────────────────────────────────────────────────────────────────────────

# Bootstrap when piped from curl (BASH_SOURCE unset) or modules are not beside install.sh.
_tsoc_bootstrap_install() {
    local install_dir="${TSOC_INSTALL_DIR:-/opt/thinking-soc-splunk-hackathon}"
    local repo_url="${TSOC_REPO_URL:-https://github.com/Sepideh-Asadollahi/ThinkingSOC-splunk-hackathon.git}"
    local branch="main"

    if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
        echo "[ERROR] Installer must run as root (use: curl … | sudo bash)" >&2
        exit 1
    fi

    if [[ -f "${install_dir}/install/modules/common.sh" ]]; then
        echo "[INFO]  Using existing checkout at ${install_dir}"
    else
        if ! command -v git >/dev/null 2>&1; then
            echo "[INFO]  Installing git (required to download installer) …"
            if command -v apt-get >/dev/null 2>&1; then
                apt-get update -qq
                apt-get install -y git ca-certificates
            else
                echo "[ERROR] git is required. Install git, then rerun the installer." >&2
                exit 1
            fi
        fi
        echo "[INFO]  Cloning repository to ${install_dir} …"
        git clone --branch "$branch" --depth 1 "$repo_url" "$install_dir"
    fi

    exec bash "${install_dir}/install.sh" "$@"
}

_tsoc_script_path="${BASH_SOURCE[0]:-}"
if [[ -n "$_tsoc_script_path" && -f "$_tsoc_script_path" ]]; then
    _tsoc_script_dir="$(cd "$(dirname "$_tsoc_script_path")" && pwd)"
else
    _tsoc_script_dir=""
fi

if [[ -z "$_tsoc_script_dir" ]] || [[ ! -f "${_tsoc_script_dir}/install/modules/common.sh" ]]; then
    _tsoc_bootstrap_install "$@"
fi

set -euo pipefail

SCRIPT_DIR="$_tsoc_script_dir"
unset _tsoc_script_path _tsoc_script_dir
# Tree where install.sh lives (used to copy bundled demo snapshot into INSTALL_DIR when needed).
INSTALL_SCRIPT_DIR="$SCRIPT_DIR"
MODULE_DIR="${SCRIPT_DIR}/install/modules"

require_module() {
    local module_path="$1"
    if [[ ! -f "$module_path" ]]; then
        echo "[ERROR] Missing required installer module: $module_path" >&2
        echo "[ERROR] Use the bootstrap one-liner (avoids stale GitHub raw cache on install.sh):" >&2
        echo "[ERROR]   curl -fsSL https://raw.githubusercontent.com/Sepideh-Asadollahi/ThinkingSOC-splunk-hackathon/main/install/bootstrap.sh | sudo bash" >&2
        echo "[ERROR] Or clone under /opt and run: cd /opt/thinking-soc-splunk-hackathon && sudo bash install.sh" >&2
        exit 1
    fi
}

require_module "${MODULE_DIR}/common.sh"
require_module "${MODULE_DIR}/prerequisites.sh"
require_module "${MODULE_DIR}/project.sh"
require_module "${MODULE_DIR}/demo_data.sh"
require_module "${MODULE_DIR}/docker_stack.sh"
require_module "${MODULE_DIR}/services.sh"
require_module "${MODULE_DIR}/smoke_and_summary.sh"
require_module "${MODULE_DIR}/embedding.sh"
require_module "${MODULE_DIR}/post_configure.sh"
require_module "${MODULE_DIR}/steps.sh"

# shellcheck disable=SC1091
source "${MODULE_DIR}/common.sh"
# shellcheck disable=SC1091
source "${MODULE_DIR}/prerequisites.sh"
# shellcheck disable=SC1091
source "${MODULE_DIR}/project.sh"
# shellcheck disable=SC1091
source "${MODULE_DIR}/demo_data.sh"
# shellcheck disable=SC1091
source "${MODULE_DIR}/docker_stack.sh"
# shellcheck disable=SC1091
source "${MODULE_DIR}/embedding.sh"
# shellcheck disable=SC1091
source "${MODULE_DIR}/services.sh"
# shellcheck disable=SC1091
source "${MODULE_DIR}/smoke_and_summary.sh"
# shellcheck disable=SC1091
source "${MODULE_DIR}/post_configure.sh"
source "${MODULE_DIR}/steps.sh"

main() {
    if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
        print_install_runtime_modes_help
        exit 0
    fi

    print_install_banner
    info "Stack can run with systemd or without — you will choose in a moment."
    info "Details: install/README.md  |  Help: sudo bash install.sh --help"
    echo ""

    need_root
    if [[ "$NON_INTERACTIVE" == "true" ]]; then
        # Keep apt/dpkg/needrestart from attempting a TTY dialog during CI,
        # cloud-init, and unattended smoke installs.
        export DEBIAN_FRONTEND="${DEBIAN_FRONTEND:-noninteractive}"
        export NEEDRESTART_MODE="${NEEDRESTART_MODE:-a}"
    fi
    detect_os
    resolve_install_dir "$SCRIPT_DIR"
    init_install_verbose
    init_install_state
    info "Detected OS: ${OS_ID} ${OS_VERSION}"
    info "Install directory: $INSTALL_DIR"
    info "Progress file: ${INSTALL_STATE_FILE:-$INSTALL_DIR/.tsoc-install-progress}"
    info "Network steps auto-retry ${TSOC_STEP_AUTO_ATTEMPTS:-3} times, then ask before retry/abort"

    if [[ "$OS_ID" != "ubuntu" && "$OS_ID" != "debian" ]]; then
        warn "This installer is designed for Ubuntu/Debian."
        if ! prompt_yn "Continue anyway?" "n"; then
            exit 0
        fi
    fi

    step "Configuration"

    local detected_ip
    detected_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
    detected_ip="${detected_ip:-127.0.0.1}"

    echo -e "  ${BOLD}Detected server IP:${NC} ${detected_ip}"
    echo "  The web interface will be accessible from any device on your network."
    echo "  Backend services (API, databases) stay on 127.0.0.1 (localhost only)."
    echo ""
    ask "Server IP or hostname for web access [${detected_ip}]:"
    user_ip="$(prompt_input "" "$detected_ip")"
    SERVER_IP="${user_ip:-$detected_ip}"
    ok "Web interface will be at: http://${SERVER_IP}:3000"
    echo ""

    LOAD_DEMO_DATA=true
    case "${TSOC_LOAD_DEMO_DATA:-}" in
        true|1|yes) LOAD_DEMO_DATA=true ;;
        false|0|no) LOAD_DEMO_DATA=false ;;
        *)
            if ! prompt_yn "Load demo data (sample users, assets, relationships, latest analysis records)?" "y"; then
                LOAD_DEMO_DATA=false
            fi
            ;;
    esac
    if [[ "$LOAD_DEMO_DATA" == true ]]; then
        demo_data_runtime_note
        if [[ -f "${INSTALL_DIR}/backend/data/demo/postgres_snapshot/manifest.json" ]] \
            || [[ -f "${INSTALL_SCRIPT_DIR}/backend/data/demo/postgres_snapshot/manifest.json" ]]; then
            ok "Full demo snapshot available (auto-load during database setup)"
        else
            warn "postgres_snapshot not in install tree — will try CSV fallback after repository step"
        fi
    fi

    prompt_embedding_model

    step "Service deployment (systemd)"
    echo ""
    echo "  After install, backend (API) and frontend (web UI) must stay running."
    echo "  Both paths use a production frontend build (npm run build + next start), not npm run dev."
    echo ""
    echo -e "  ${BOLD}[1] Yes — WITH systemd${NC} (recommended)"
    echo "    · Units tsoc-backend (:9876) + tsoc-frontend (:3000), auto-start on boot"
    echo "    · Manage: sudo systemctl status|start|stop|restart tsoc-backend tsoc-frontend"
    echo "    · Logs:   sudo journalctl -u tsoc-backend -f"
    echo ""
    echo -e "  ${BOLD}[2] No — WITHOUT systemd${NC} (background)"
    echo "    · Same production UI (npm run start), processes under logs/"
    echo "    · Manage: sudo bash $INSTALL_DIR/scripts/start-tsoc-services.sh"
    echo "    · Logs:   tail -f $INSTALL_DIR/logs/backend.log $INSTALL_DIR/logs/frontend.log"
    echo "    · Later:  sudo bash $INSTALL_DIR/scripts/install-systemd.sh  → switch to [1]"
    echo ""
    echo "  Guide: install/README.md"
    echo ""
    SETUP_SYSTEMD=false
    case "${TSOC_SETUP_SYSTEMD:-}" in
        true|1|yes) SETUP_SYSTEMD=true ;;
        false|0|no) SETUP_SYSTEMD=false ;;
        *)
            if prompt_yn "Create systemd services (tsoc-backend + tsoc-frontend)?" "y"; then
                SETUP_SYSTEMD=true
            fi
            ;;
    esac
    if [[ "$SETUP_SYSTEMD" == true ]]; then
        ok "Selected: systemd (auto-start on boot)"
    else
        ok "Selected: background production services (no systemd)"
    fi
    echo ""

    if ! command_exists node; then
        cleanup_stale_nodesource_apt
    fi

    run_install_step system-update "System Update" "apt mirrors / network" true \
        _step_system_update

    run_install_step prerequisites "Prerequisites" "apt / Docker / NodeSource" true \
        _step_prerequisites

    run_install_step python-bootstrap "Python bootstrap" "apt python-venv / CA certs" true \
        _step_python_bootstrap

    run_install_step repository "Repository" "git clone" true \
        _step_repository

    run_install_step backend-venv "Python Virtual Environment" "PyPI / pip" true \
        _step_backend_venv

    run_install_step backend-env "Backend Configuration" "local .env file" true \
        _step_backend_env

    run_install_step docker-images "Docker images" "Docker Hub registry" true \
        _step_docker_images

    run_install_step docker-stack "Docker stack" "ThinkingSOC containers + volumes" true \
        _step_prepare_tsoc_docker_stack

    run_install_step project-setup "Project Setup" "Docker stack / database / seed" true \
        _step_project_setup

    run_install_step frontend "Frontend" "npm registry" true \
        _step_frontend

    run_install_step frontend-build "Frontend production build" "npm / Next.js build" true \
        _step_frontend_build

    run_install_step embedding-model "Vector embedding model" "FastEmbed ONNX download" true \
        _step_embedding_model

    if [[ "$SETUP_SYSTEMD" == true ]]; then
        run_install_step systemd "Systemd Services" "service units" true \
            create_systemd_services
    else
        run_install_step services-start "Start Services" "backend API and frontend UI" true \
            _step_start_services
    fi

    if [[ "$LOAD_DEMO_DATA" == true ]]; then
        run_install_step demo-load "Demo data" "PostgreSQL + service reload" true \
            _step_apply_demo_and_restart_services
    fi

    # Smoke test is informational only: run ONCE, never loop/retry, never abort.
    # The installer must always reach the final summary (backend may still be
    # warming up the embedding model in the background — that is not a failure).
    step "Smoke Test"
    run_smoke_test || warn "Some smoke checks did not pass yet — install is complete; services may still be warming up (see notes above)."

    print_summary
    run_post_install_configure

    step "Reload application services"
    info "Restarting backend and frontend so final configuration is active (automatic) …"
    if _pc_restart_tsoc_services_for_env; then
        ok "Install complete — backend and frontend restarted and verified"
    else
        warn "Final automatic restart did not fully verify — retrying once …"
        sleep 3
        if _pc_restart_tsoc_services_for_env; then
            ok "Install complete — services restarted on retry"
        else
            warn "Services may still be warming up; check: systemctl status tsoc-backend tsoc-frontend"
        fi
    fi
}

main "$@"
