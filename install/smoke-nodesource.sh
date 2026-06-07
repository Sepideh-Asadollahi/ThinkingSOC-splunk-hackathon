#!/usr/bin/env bash
# Smoke test: NodeSource GPG + apt repo setup (install/modules/prerequisites.sh)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="${SCRIPT_DIR}/modules"

# shellcheck disable=SC1091
source "${MODULE_DIR}/common.sh"
# shellcheck disable=SC1091
source "${MODULE_DIR}/prerequisites.sh"

need_root
detect_os

pass=0
fail=0
smoke_ok() { ok "  $1"; pass=$((pass + 1)); }
smoke_fail() { err "  $1"; fail=$((fail + 1)); }

step "NodeSource smoke test"

info "Simulating broken prior install (sources without GPG key) ..."
node_arch="$(dpkg --print-architecture)"
mkdir -p /etc/apt/keyrings
rm -f /etc/apt/keyrings/nodesource.gpg "${NODE_KEYRING}"
cat > /etc/apt/sources.list.d/nodesource.sources <<-BROKEN
Types: deb
URIs: https://deb.nodesource.com/node_${PREFERRED_NODE_MAJOR}.x
Suites: nodistro
Components: main
Architectures: ${node_arch}
Signed-By: /etc/apt/keyrings/nodesource.gpg
BROKEN

if apt-get update -qq 2>/dev/null; then
    err "  Expected apt update to fail with missing key (simulation broken)"
    fail=$((fail + 1))
else
    ok "  apt update fails without key (expected)"
    pass=$((pass + 1))
fi

info "Applying installer NodeSource fix ..."
cleanup_stale_nodesource_apt
install_nodesource_gpg_key
write_nodesource_apt_source "$node_arch"

if apt_update_lists; then
    ok "  apt update succeeds with refreshed NodeSource key"
    pass=$((pass + 1))
else
    err "  apt update still fails after key refresh"
    fail=$((fail + 1))
    exit 1
fi

[[ -f "${NODE_KEYRING}" && -r "${NODE_KEYRING}" ]] && smoke_ok "NodeSource keyring at ${NODE_KEYRING}" || smoke_fail "NodeSource keyring missing"
grep -q "${NODE_KEYRING}" /etc/apt/sources.list.d/nodesource.sources && \
    smoke_ok "nodesource.sources Signed-By path correct" || smoke_fail "nodesource.sources Signed-By mismatch"

node_major=0
if command_exists node; then
    node_major="$(node --version | sed 's/^v//' | cut -d. -f1)"
fi
if ! command_exists node || [[ "$node_major" -lt "$MIN_NODE_MAJOR" ]]; then
    info "Installing nodejs package from NodeSource ..."
    apt_install_packages nodejs
fi

node_ver="$(node --version 2>/dev/null || echo none)"
node_major="${node_ver#v}"
node_major="${node_major%%.*}"
if [[ "$node_major" =~ ^[0-9]+$ ]] && [[ "$node_major" -ge "$MIN_NODE_MAJOR" ]]; then
    ok "  Node.js ${node_ver} (>= v${MIN_NODE_MAJOR})"
    pass=$((pass + 1))
else
    err "  Node.js version insufficient: ${node_ver}"
    fail=$((fail + 1))
fi

echo ""
if [[ $fail -eq 0 ]]; then
    ok "NodeSource smoke test passed: ${pass} checks OK"
    exit 0
fi
warn "NodeSource smoke test: ${pass} passed, ${fail} failed"
exit 1
