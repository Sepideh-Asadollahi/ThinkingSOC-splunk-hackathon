#!/usr/bin/env bash
# Start ThinkingSOC Lite backend + frontend (production UI: npm run build + npm run start).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export INSTALL_DIR="${TSOC_INSTALL_DIR:-$ROOT}"

# shellcheck disable=SC1091
source "${ROOT}/install/modules/common.sh"
# shellcheck disable=SC1091
source "${ROOT}/install/modules/services.sh"

VENV_PYTHON="${INSTALL_DIR}/backend/.venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
    err "Missing ${VENV_PYTHON} — run install.sh first"
    exit 1
fi

start_application_services
