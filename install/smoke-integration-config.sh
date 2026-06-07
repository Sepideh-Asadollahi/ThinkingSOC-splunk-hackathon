#!/usr/bin/env bash
# Smoke test: post-install Splunk / LiteLLM / MCP configuration (backend/.env + live checks)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODULE_DIR="${SCRIPT_DIR}/modules"

for mod in common.sh project.sh embedding.sh services.sh post_configure.sh; do
    if [[ ! -f "${MODULE_DIR}/${mod}" ]]; then
        echo "[ERROR] Missing installer module: ${MODULE_DIR}/${mod}" >&2
        exit 1
    fi
done

# shellcheck disable=SC1091
source "${MODULE_DIR}/common.sh"
# shellcheck disable=SC1091
source "${MODULE_DIR}/project.sh"
# shellcheck disable=SC1091
source "${MODULE_DIR}/embedding.sh"
# shellcheck disable=SC1091
source "${MODULE_DIR}/services.sh"
# shellcheck disable=SC1091
source "${MODULE_DIR}/post_configure.sh"

INSTALL_DIR="${TSOC_INSTALL_DIR:-$INSTALL_DIR}"
VENV_PYTHON="${INSTALL_DIR}/backend/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    err "Backend venv missing — run install.sh first: $VENV_PYTHON"
    exit 1
fi

run_integration_configure_smoke
exit $?
