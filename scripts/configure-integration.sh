#!/usr/bin/env bash
# Re-run post-install Splunk / LiteLLM / MCP configuration wizard.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODULE_DIR="${INSTALL_DIR}/install/modules"

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

if [[ "${1:-}" == "--smoke" || "${1:-}" == "--smoke-only" ]]; then
    run_integration_configure_smoke
    exit $?
fi

if [[ $EUID -ne 0 ]]; then
    err "Run as root: sudo bash scripts/configure-integration.sh"
    err "Smoke only (no root): bash scripts/configure-integration.sh --smoke"
    exit 1
fi

if [[ -f /etc/systemd/system/tsoc-backend.service ]] && systemctl is-enabled tsoc-backend &>/dev/null; then
    SETUP_SYSTEMD=true
else
    SETUP_SYSTEMD=false
fi

run_post_install_configure
