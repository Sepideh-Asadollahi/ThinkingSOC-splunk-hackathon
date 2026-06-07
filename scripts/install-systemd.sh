#!/usr/bin/env bash
# Create tsoc-backend + tsoc-frontend systemd units when you answered "No" during install.sh.
# Prefer answering "Yes" to the systemd prompt in: sudo bash install.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export INSTALL_DIR="${TSOC_INSTALL_DIR:-$ROOT}"

# shellcheck disable=SC1091
source "${ROOT}/install/modules/common.sh"
# shellcheck disable=SC1091
source "${ROOT}/install/modules/services.sh"

need_root

VENV_PYTHON="${INSTALL_DIR}/backend/.venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
    err "Missing ${VENV_PYTHON} — run install.sh first"
    exit 1
fi

if [[ ! -d "${INSTALL_DIR}/frontend/node_modules" ]]; then
    err "Frontend not installed — run install.sh frontend step or: cd frontend && npm install"
    exit 1
fi

ensure_frontend_production_build || exit 1

create_systemd_services

echo ""
print_systemd_control_help
