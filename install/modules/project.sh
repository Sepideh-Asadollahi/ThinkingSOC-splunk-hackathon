#!/usr/bin/env bash

setup_repo() {
    validate_repo_url
    if [[ -d "$INSTALL_DIR/.git" ]] || is_tsoc_repo_root "$INSTALL_DIR"; then
        ok "Using existing checkout at $INSTALL_DIR"
    else
        _git_clone_repo || return 1
        ok "Repository cloned"
    fi
}

_git_clone_repo() {
    info "Cloning repository to $INSTALL_DIR ..."
    if [[ "$INSTALL_VERBOSE" == true ]]; then
        run_cmd git clone --progress --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
    else
        git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
    fi
}

setup_venv() {
    local venv_dir="$INSTALL_DIR/backend/.venv"
    local venv_python="$venv_dir/bin/python"
    local requirements="$INSTALL_DIR/backend/requirements.txt"

    ensure_python_venv_package

    if [[ -d "$venv_dir" ]] && [[ ! -x "$venv_python" ]]; then
        warn "Removing incomplete virtual environment at $venv_dir"
        rm -rf "$venv_dir"
    fi

    if [[ -f "$venv_python" ]]; then
        ok "Virtual environment exists at $venv_dir"
    else
        info "Creating virtual environment ..."
        run_cmd "$PYTHON_CMD" -m venv "$venv_dir"
        ok "Virtual environment created at $venv_dir"
    fi

    maybe_upgrade_venv_pip "$venv_python"

    local venv_dir="$INSTALL_DIR/backend/.venv"
    configure_venv_pip_network "$venv_dir"

    if [[ -f "$requirements" ]]; then
        info "Installing Python dependencies (this may take a minute) ..."
        venv_pip_install "$venv_python" -r "$requirements" || return 1
        verify_venv_python_deps "$venv_python" "$requirements" || return 1
    else
        warn "requirements.txt not found — skipping pip install"
    fi

    VENV_PYTHON="$venv_python"
}

setup_backend_env() {
    local env_file="$INSTALL_DIR/backend/.env"
    local env_example="$INSTALL_DIR/backend/.env.example"

    if [[ -f "$env_file" ]]; then
        ok "backend/.env already exists — keeping current config"
        _ensure_backend_env_defaults
        return 0
    fi

    if [[ ! -f "$env_example" ]]; then
        err "backend/.env.example missing — cannot create backend/.env"
        return 1
    fi

    cp "$env_example" "$env_file"
    _apply_install_embedding_defaults "$env_file"
    ok "Created backend/.env (embedding model: ${EMBEDDING_MODEL:-bge-base}, ${EMBEDDING_DIM:-768}-dim)"
}

_fastembed_cache_dir() {
    echo "/opt/.thinking-soc-cache/fastembed"
}

_ensure_backend_env_defaults() {
    local env_file="$INSTALL_DIR/backend/.env"
    [[ -f "$env_file" ]] || return 0
    local cache_dir
    cache_dir="$(_fastembed_cache_dir)"
    mkdir -p "$cache_dir"
    _upsert_env_default "$env_file" "TSOC_FASTEMBED_CACHE_DIR" "$cache_dir"
    _ensure_ingest_auto_analyze_env "$env_file" false
}

_ensure_ingest_auto_analyze_env() {
    local env_file="$1"
    local force="${2:-false}"
    [[ -f "$env_file" ]] || return 0
    if [[ "$force" == "true" ]]; then
        _upsert_env_line "$env_file" "TSOC_INGEST_AUTO_ANALYZE" "true"
        _upsert_env_line "$env_file" "TSOC_INGEST_AUTO_ANALYZE_PIPELINE" "triage"
    else
        _upsert_env_default "$env_file" "TSOC_INGEST_AUTO_ANALYZE" "true"
        _upsert_env_default "$env_file" "TSOC_INGEST_AUTO_ANALYZE_PIPELINE" "triage"
    fi
}

_apply_install_embedding_defaults() {
    local env_file="$1"
    local cache_dir
    cache_dir="$(_fastembed_cache_dir)"
    mkdir -p "$cache_dir"
    # Honors the install-time picker (prompt_embedding_model); default = medium (bge-base, ~220 MB).
    _upsert_env_line "$env_file" "TSOC_EMBEDDING_MODEL" "${EMBEDDING_MODEL:-bge-base}"
    _upsert_env_line "$env_file" "TSOC_EMBEDDING_DIM" "${EMBEDDING_DIM:-768}"
    _upsert_env_line "$env_file" "TSOC_FASTEMBED_CACHE_DIR" "$cache_dir"
    _ensure_ingest_auto_analyze_env "$env_file" true
}

_run_setup_py_once() {
    local seed_flag="$1"
    cd "$INSTALL_DIR"
    if [[ "$INSTALL_VERBOSE" == true ]]; then
        env TSOC_INSTALL_VERBOSE=1 TSOC_SETUP_PREREQ_OK=1 "$VENV_PYTHON" setup.py --start-postgres --skip-pip $seed_flag -v
    else
        TSOC_SETUP_PREREQ_OK=1 "$VENV_PYTHON" setup.py --start-postgres --skip-pip $seed_flag -v
    fi
}

setup_frontend() {
    cd "$INSTALL_DIR/frontend"

    if [[ -f .env.local ]]; then
        ok "frontend/.env.local already exists — keeping current config"
        _ensure_frontend_env_defaults
    else
        local auth_secret
        auth_secret="$(openssl rand -base64 42)"

        cat > .env.local <<ENVEOF
AUTH_SECRET=${auth_secret}

TSOC_DEMO_USER=admin
TSOC_DEMO_PASSWORD=123456@a

TSOC_BACKEND_URL=http://127.0.0.1:9876
TSOC_INGEST_TOKEN=
TSOC_DEV_ORIGIN=127.0.0.1,localhost,${SERVER_IP}

NEXT_PUBLIC_TSOC_APP_URL=http://${SERVER_IP}:3000
NEXT_PUBLIC_TSOC_SPLUNK_HOST=127.0.0.1
NEXT_PUBLIC_TSOC_SPLUNK_PORT=8089
ENVEOF
        ok "Created frontend/.env.local (web access: ${SERVER_IP})"
    fi

    _sync_frontend_ingest_token_from_backend

    info "Installing frontend dependencies ..."
    _npm_install_deps || return 1
    ok "Frontend dependencies installed"
}

_ensure_frontend_env_defaults() {
    local env_file="$INSTALL_DIR/frontend/.env.local"
    [[ -f "$env_file" ]] || return 0
    _upsert_env_default "$env_file" "TSOC_DEMO_USER" "admin"
    _upsert_env_default "$env_file" "TSOC_DEMO_PASSWORD" "123456@a"
    _upsert_env_default "$env_file" "TSOC_BACKEND_URL" "http://127.0.0.1:9876"
    if [[ -n "${SERVER_IP:-}" ]]; then
        local origins="127.0.0.1,localhost,${SERVER_IP}"
        if grep -qE '^TSOC_DEV_ORIGIN=' "$env_file" 2>/dev/null; then
            if ! grep -E '^TSOC_DEV_ORIGIN=' "$env_file" | grep -qF "${SERVER_IP}"; then
                local current
                current="$(grep -E '^TSOC_DEV_ORIGIN=' "$env_file" | head -1 | cut -d= -f2-)"
                _upsert_env_line "$env_file" "TSOC_DEV_ORIGIN" "${current},${SERVER_IP}"
            fi
        else
            _upsert_env_default "$env_file" "TSOC_DEV_ORIGIN" "$origins"
        fi
        _upsert_env_default "$env_file" "NEXT_PUBLIC_TSOC_APP_URL" "http://${SERVER_IP}:3000"
    fi
    _sync_frontend_ingest_token_from_backend
}

# UI proxy sends Authorization: Bearer $TSOC_INGEST_TOKEN — must match backend when token is set.
_sync_frontend_ingest_token_from_backend() {
    local backend_env="$INSTALL_DIR/backend/.env"
    local frontend_env="$INSTALL_DIR/frontend/.env.local"
    [[ -f "$backend_env" && -f "$frontend_env" ]] || return 0
    local tok
    tok="$(grep -E '^TSOC_INGEST_TOKEN=' "$backend_env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    if [[ -n "$tok" ]]; then
        _upsert_env_line "$frontend_env" "TSOC_INGEST_TOKEN" "$tok"
    fi
}

_upsert_env_default() {
    local file="$1" key="$2" value="$3"
    if grep -qE "^[[:space:]]*${key}=" "$file" 2>/dev/null; then
        return 0
    fi
    echo "${key}=${value}" >>"$file"
}

_upsert_env_line() {
    local file="$1" key="$2" value="$3"
    if grep -qE "^[[:space:]]*${key}=" "$file" 2>/dev/null; then
        sed -i "s|^[[:space:]]*${key}=.*|${key}=${value}|" "$file"
    else
        echo "${key}=${value}" >>"$file"
    fi
}

_npm_install_deps() {
    if [[ "$INSTALL_VERBOSE" == true ]]; then
        run_cmd npm install --no-audit --no-fund
    else
        npm install --no-audit --no-fund
    fi
}
