#!/usr/bin/env bash

# ── Check All Prerequisites ──────────────────────────────────────────────────
NEED_CORE_TOOLS=false
NEED_GIT=false
NEED_DOCKER=false
NEED_DOCKER_DAEMON=false
NEED_COMPOSE=false
NEED_PYTHON=false
NEED_PYTHON_VENV=false
NEED_PYTHON_PIP=false
NEED_NODE=false
PYTHON_CMD=""

detect_python_cmd() {
    PYTHON_CMD=""
    for candidate in python3.12 python3.11 python3; do
        if command_exists "$candidate"; then
            local ver
            ver="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")"
            local major="${ver%%.*}" minor="${ver##*.}"
            if [[ "$major" -gt 3 || ( "$major" -eq 3 && "$minor" -ge "$MIN_PYTHON_MINOR" ) ]]; then
                PYTHON_CMD="$candidate"
                return 0
            fi
        fi
    done
    return 1
}

# Debian ships python3.x without ensurepip unless python3.x-venv is installed.
# "import venv" alone is not a reliable check on Ubuntu/Debian.
python_can_create_venv() {
    local py="$1"
    [[ -n "$py" ]] && command_exists "$py" && "$py" -c "import ensurepip" 2>/dev/null
}

ensure_python_venv_package() {
    detect_python_cmd || true
    if [[ -z "$PYTHON_CMD" ]]; then
        err "Python 3.${MIN_PYTHON_MINOR}+ is required."
        return 1
    fi
    if python_can_create_venv "$PYTHON_CMD"; then
        return 0
    fi

    ensure_apt_updated
    local short_ver
    short_ver="$("$PYTHON_CMD" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    local venv_pkg="python${short_ver}-venv"
    info "Installing ${venv_pkg} (provides ensurepip for venv) ..."
    if ! apt-cache show "$venv_pkg" &>/dev/null 2>&1; then
        err "Package ${venv_pkg} is not available from apt on this system."
        err "Install it manually (e.g. apt install ${venv_pkg}), then rerun install.sh."
        return 1
    fi
    apt_install_packages "$venv_pkg" || return 1
    if ! python_can_create_venv "$PYTHON_CMD"; then
        err "${venv_pkg} was installed but ensurepip is still unavailable."
        return 1
    fi
    ok "Python ensurepip/venv ready for $("$PYTHON_CMD" --version 2>&1)"
}

ensure_ca_certificates() {
    ensure_apt_updated
    apt_install_packages ca-certificates
    if command_exists update-ca-certificates; then
        update-ca-certificates >/dev/null 2>&1 || true
    fi
}

check_all_prerequisites() {
    info "Checking installed components ..."
    echo ""

    local core_ok=true
    for tool in curl openssl gpg; do
        if command_exists "$tool"; then
            ok "$tool"
        else
            core_ok=false
            warn "$tool — NOT FOUND"
        fi
    done
    if [[ "$core_ok" == false ]]; then
        NEED_CORE_TOOLS=true
    fi

    if command_exists git; then
        ok "git $(git --version | awk '{print $3}')"
    else
        NEED_GIT=true
        warn "git — NOT FOUND"
    fi

    if command_exists docker; then
        ok "Docker $(docker --version | awk '{print $3}' | tr -d ',')"
        if docker info &>/dev/null; then
            ok "Docker daemon running"
        else
            NEED_DOCKER_DAEMON=true
            warn "Docker daemon — NOT RUNNING"
        fi
    else
        NEED_DOCKER=true
        NEED_DOCKER_DAEMON=true
        warn "Docker — NOT FOUND"
    fi

    if docker compose version &>/dev/null 2>&1; then
        ok "Docker Compose $(docker compose version --short 2>/dev/null || echo 'v2')"
    elif command_exists docker-compose; then
        ok "docker-compose (legacy v1)"
    else
        NEED_COMPOSE=true
        warn "Docker Compose — NOT FOUND"
    fi

    detect_python_cmd || true

    if [[ -n "$PYTHON_CMD" ]]; then
        ok "Python $("$PYTHON_CMD" --version 2>&1 | awk '{print $2}')"

        if python_can_create_venv "$PYTHON_CMD"; then
            ok "Python venv (ensurepip)"
        else
            NEED_PYTHON_VENV=true
            warn "Python venv/ensurepip — NOT FOUND (install python${MIN_PYTHON_MINOR}-venv)"
        fi

        if "$PYTHON_CMD" -m pip --version &>/dev/null; then
            ok "pip $("$PYTHON_CMD" -m pip --version 2>&1 | awk '{print $2}')"
        else
            NEED_PYTHON_PIP=true
            warn "pip — NOT FOUND"
        fi
    else
        NEED_PYTHON=true
        NEED_PYTHON_VENV=true
        NEED_PYTHON_PIP=true
        warn "Python 3.${MIN_PYTHON_MINOR}+ — NOT FOUND"
    fi

    if command_exists node; then
        local node_ver
        node_ver="$(node --version | tr -d 'v')"
        local node_major="${node_ver%%.*}"
        if [[ "$node_major" -ge "$MIN_NODE_MAJOR" ]]; then
            ok "Node.js v${node_ver}"
        else
            NEED_NODE=true
            warn "Node.js v${node_ver} found — v${MIN_NODE_MAJOR}+ REQUIRED"
        fi
    else
        NEED_NODE=true
        warn "Node.js — NOT FOUND"
    fi

    echo ""
    local missing=()
    $NEED_CORE_TOOLS && missing+=("curl/openssl/gpg")
    $NEED_GIT && missing+=("git")
    $NEED_DOCKER && missing+=("Docker")
    $NEED_DOCKER_DAEMON && [[ "$NEED_DOCKER" == false ]] && missing+=("Docker daemon")
    $NEED_COMPOSE && missing+=("Docker Compose")
    $NEED_PYTHON && missing+=("Python 3.${MIN_PYTHON_MINOR}+")
    $NEED_PYTHON_VENV && [[ "$NEED_PYTHON" == false ]] && missing+=("python-venv")
    $NEED_PYTHON_PIP && [[ "$NEED_PYTHON" == false ]] && missing+=("pip")
    $NEED_NODE && missing+=("Node.js 20+")

    if [[ ${#missing[@]} -eq 0 ]]; then
        ok "All prerequisites are already installed!"
        return 0
    fi

    warn "Missing components: ${missing[*]}"
    echo ""
    if ! prompt_yn "Install missing components now?" "y"; then
        err "Cannot continue without prerequisites."
        exit 1
    fi
    return 1
}

# ── NodeSource (Node.js) apt setup ───────────────────────────────────────────
# NodeSource rotated GPG keys (SHA-512) in 2026; stale keyrings cause NO_PUBKEY /
# SHA1 rejection on modern Ubuntu/Debian. Always refresh the key and use the path
# documented by NodeSource: /usr/share/keyrings/nodesource.gpg
NODE_KEYRING="/usr/share/keyrings/nodesource.gpg"
NODE_KEY_URL="https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key"

cleanup_stale_nodesource_apt() {
    rm -f /etc/apt/sources.list.d/nodesource.list \
          /etc/apt/sources.list.d/nodesource.sources \
          /etc/apt/keyrings/nodesource.gpg \
          "${NODE_KEYRING}"
}

install_nodesource_gpg_key() {
    mkdir -p /usr/share/keyrings /etc/apt/keyrings
    info "Installing NodeSource GPG key ..."
    if [[ "$INSTALL_VERBOSE" == true ]]; then
        run_cmd bash -c "curl -fL --progress-bar '${NODE_KEY_URL}' | gpg --dearmor -o '${NODE_KEYRING}'"
    else
        curl -fsSL "${NODE_KEY_URL}" | gpg --dearmor -o "${NODE_KEYRING}"
    fi
    chmod a+r "${NODE_KEYRING}"
}

write_nodesource_apt_source() {
    local node_arch="$1"
    cat > /etc/apt/sources.list.d/nodesource.sources <<-NSRC
Types: deb
URIs: https://deb.nodesource.com/node_${PREFERRED_NODE_MAJOR}.x
Suites: nodistro
Components: main
Architectures: ${node_arch}
Signed-By: ${NODE_KEYRING}
NSRC
}

install_nodesource_via_setup_script() {
    local setup_url="https://deb.nodesource.com/setup_${PREFERRED_NODE_MAJOR}.x"
    warn "NodeSource apt update failed; using official setup script ..."
    cleanup_stale_nodesource_apt
    if [[ "$INSTALL_VERBOSE" == true ]]; then
        run_cmd bash -c "curl -fsSL '${setup_url}' | bash -"
    else
        bash -c "curl -fsSL '${setup_url}' | bash -"
    fi
}

# ── Install Missing Prerequisites ────────────────────────────────────────────
apt_updated=false

ensure_apt_updated() {
    if [[ "$apt_updated" == false ]]; then
        info "Updating package lists ..."
        apt_update_lists
        apt_updated=true
    fi
}

install_missing_prerequisites() {
    if $NEED_CORE_TOOLS; then
        ensure_apt_updated
        info "Installing core tools (curl, openssl, gnupg) ..."
        apt_install_packages curl openssl gnupg ca-certificates
        ok "Core tools installed"
    fi

    if $NEED_GIT; then
        ensure_apt_updated
        info "Installing git ..."
        apt_install_packages git
        ok "git installed"
    fi

    if $NEED_DOCKER; then
        ensure_apt_updated
        info "Installing Docker (official repo) ..."
        info "Removing conflicting Docker packages from distro repos (if any) ..."
        apt_remove_packages docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc
        apt_install_packages ca-certificates curl

        install -m 0755 -d /etc/apt/keyrings
        if [[ ! -f /etc/apt/keyrings/docker.asc ]]; then
            curl_fetch "https://download.docker.com/linux/${OS_ID}/gpg" -o /etc/apt/keyrings/docker.asc
            chmod a+r /etc/apt/keyrings/docker.asc
        fi

        local suite
        suite="$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")"
        if [[ -z "$suite" ]]; then
            err "Could not detect OS codename for Docker repository."
            err "Set VERSION_CODENAME/UBUNTU_CODENAME correctly or install Docker manually first."
            return 1
        fi

        cat > /etc/apt/sources.list.d/docker.sources <<-SRCEOF
Types: deb
URIs: https://download.docker.com/linux/${OS_ID}
Suites: ${suite}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
SRCEOF

        apt_update_lists
        apt_updated=true
        apt_install_packages docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        NEED_COMPOSE=false
        ok "Docker + Docker Compose installed"
    fi

    if $NEED_DOCKER_DAEMON; then
        info "Starting Docker daemon ..."
        run_cmd systemctl enable --now docker
        ok "Docker daemon started"
    fi

    if $NEED_COMPOSE; then
        ensure_apt_updated
        info "Installing Docker Compose plugin ..."
        apt_install_packages docker-compose-plugin
        if docker compose version &>/dev/null; then
            ok "Docker Compose installed"
            NEED_COMPOSE=false
        else
            err "Could not install Docker Compose automatically."
            return 1
        fi
    fi

    if $NEED_PYTHON; then
        ensure_apt_updated
        info "Installing Python ..."
        if apt-cache show python3.12 &>/dev/null 2>&1; then
            apt_install_packages python3.12 python3.12-venv python3.12-dev
            PYTHON_CMD="python3.12"
        elif apt-cache show python3.11 &>/dev/null 2>&1; then
            apt_install_packages python3.11 python3.11-venv python3.11-dev
            PYTHON_CMD="python3.11"
        else
            if [[ "$OS_ID" == "ubuntu" ]]; then
                apt_install_packages software-properties-common
                run_cmd add-apt-repository -y ppa:deadsnakes/ppa
                apt_update_lists
                apt_updated=true
                apt_install_packages python3.12 python3.12-venv python3.12-dev
                PYTHON_CMD="python3.12"
            else
                err "Python 3.${MIN_PYTHON_MINOR}+ package not available on this Debian release."
                return 1
            fi
        fi
        NEED_PYTHON_VENV=false
        NEED_PYTHON_PIP=false
        ok "Python installed: $("$PYTHON_CMD" --version 2>&1)"
    fi

    if $NEED_PYTHON_VENV; then
        ensure_python_venv_package
        NEED_PYTHON_VENV=false
    fi

    if $NEED_PYTHON_PIP; then
        ensure_apt_updated
        info "Installing pip ..."
        apt_install_packages python3-pip 2>/dev/null || true
        ok "pip installed"
    fi

    if $NEED_NODE; then
        local node_arch
        node_arch="$(dpkg --print-architecture)"
        if [[ "$node_arch" != "amd64" && "$node_arch" != "arm64" ]]; then
            err "NodeSource Node.js ${PREFERRED_NODE_MAJOR}.x supports amd64/arm64 only (detected: ${node_arch})."
            return 1
        fi

        cleanup_stale_nodesource_apt
        ensure_apt_updated
        info "Installing Node.js ${PREFERRED_NODE_MAJOR} LTS (NodeSource repo) ..."
        apt_install_packages ca-certificates curl gnupg

        install_nodesource_gpg_key
        write_nodesource_apt_source "$node_arch"

        if ! apt_update_lists; then
            install_nodesource_via_setup_script
        fi
        apt_updated=true
        apt_install_packages nodejs
        ok "Node.js $(node --version) installed"
    fi

    detect_python_cmd || true
    echo ""
    ok "All prerequisites ready!"
}
