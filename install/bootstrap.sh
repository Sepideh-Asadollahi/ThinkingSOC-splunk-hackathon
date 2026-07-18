#!/usr/bin/env bash
# ThinkingSOC Lite — one-liner bootstrap (safe for: curl … | sudo bash)
# Does not use BASH_SOURCE or install/modules; clones repo then runs install.sh.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Sepideh-Asadollahi/ThinkingSOC-splunk-hackathon/main/install/bootstrap.sh | sudo bash
#
set -euo pipefail

INSTALL_DIR="${TSOC_INSTALL_DIR:-/opt/thinking-soc-splunk-hackathon}"
REPO_URL="${TSOC_REPO_URL:-https://github.com/Sepideh-Asadollahi/ThinkingSOC-splunk-hackathon.git}"
BRANCH="${TSOC_REPO_BRANCH:-main}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "[ERROR] Installer must run as root (use: curl … | sudo bash)" >&2
    exit 1
fi

_ensure_git() {
    if command -v git >/dev/null 2>&1; then
        return 0
    fi
    echo "[INFO]  Installing git (required to download installer) …"
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "[ERROR] git is required. Install git, then rerun the installer." >&2
        exit 1
    fi
    apt-get update -qq
    apt-get install -y git ca-certificates
}

_sync_checkout() {
    echo "[INFO]  Updating checkout at ${INSTALL_DIR} …"
    git -C "$INSTALL_DIR" fetch --depth 1 origin "$BRANCH"
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git -C "$INSTALL_DIR" reset --hard "origin/${BRANCH}"
}

if [[ -f "${INSTALL_DIR}/install/modules/common.sh" ]]; then
    if [[ -d "${INSTALL_DIR}/.git" ]]; then
        _ensure_git
        _sync_checkout
    fi
    echo "[INFO]  Using checkout at ${INSTALL_DIR}"
elif [[ -d "${INSTALL_DIR}/.git" ]]; then
    _ensure_git
    _sync_checkout
elif [[ -e "${INSTALL_DIR}" ]]; then
    echo "[ERROR] ${INSTALL_DIR} exists but is not a ThinkingSOC Lite checkout." >&2
    echo "[ERROR] Remove it, set TSOC_INSTALL_DIR, or clone manually." >&2
    exit 1
else
    _ensure_git
    echo "[INFO]  Cloning repository to ${INSTALL_DIR} …"
    git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

if [[ ! -f "${INSTALL_DIR}/install.sh" ]]; then
    echo "[ERROR] Checkout incomplete — install.sh missing in ${INSTALL_DIR}" >&2
    exit 1
fi

exec bash "${INSTALL_DIR}/install.sh" "$@"
