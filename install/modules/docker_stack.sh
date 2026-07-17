#!/usr/bin/env bash

# Images must match setup_tool/docker.py STACK_IMAGES
TSOC_DOCKER_IMAGES=(
    "postgres:16-alpine"
    "qdrant/qdrant:v1.18.0"
    "neo4j:5.26-community"
)

# Must match backend/docker-compose.yml container_name and setup_tool/docker.py *CONTAINER
TSOC_STACK_CONTAINERS=(
    tsoc-postgres
    tsoc-qdrant
    tsoc-neo4j
)

# Must match docker-compose.yml volume `name:` and setup_tool/docker.py *VOLUME
TSOC_STACK_VOLUMES=(
    tsoc_pgdata
    tsoc_qdrant_data
    tsoc_neo4j_data
)

# Older compose runs from backend/ without explicit volume name: (project)_tsoc_*
TSOC_LEGACY_COMPOSE_VOLUMES=(
    backend_tsoc_pgdata
    backend_tsoc_qdrant_data
    backend_tsoc_neo4j_data
)

# Stable compose project (pairs with top-level `name: tsoc` in docker-compose.yml)
TSOC_COMPOSE_PROJECT_NAME=tsoc

# Set by _tsoc_compose_executable: (docker compose) or (docker-compose)
TSOC_COMPOSE_CMD=()

_tsoc_compose_executable() {
    TSOC_COMPOSE_CMD=()
    if docker compose version &>/dev/null 2>&1; then
        TSOC_COMPOSE_CMD=(docker compose)
        return 0
    fi
    if command_exists docker-compose; then
        TSOC_COMPOSE_CMD=(docker-compose)
        return 0
    fi
    return 1
}

_tsoc_enumerate_stack_volumes() {
    local v vol
    for v in "${TSOC_STACK_VOLUMES[@]}" "${TSOC_LEGACY_COMPOSE_VOLUMES[@]}"; do
        if docker volume inspect "$v" &>/dev/null 2>&1; then
            echo "$v"
        fi
    done
    while read -r vol; do
        [[ -n "$vol" ]] || continue
        echo "$vol"
    done < <(docker volume ls -q 2>/dev/null | grep -E 'tsoc_(pgdata|qdrant_data|neo4j_data)$' || true)
}

_tsoc_compose_in_backend() {
    # shellcheck disable=SC2091
    (
        cd "${INSTALL_DIR}/backend"
        export COMPOSE_PROJECT_NAME="${TSOC_COMPOSE_PROJECT_NAME}"
        run_cmd "${TSOC_COMPOSE_CMD[@]}" "$@"
    )
}

_tsoc_docker_stack_detected() {
    local c
    for c in "${TSOC_STACK_CONTAINERS[@]}"; do
        if docker ps -a --filter "name=^${c}$" -q 2>/dev/null | grep -q .; then
            return 0
        fi
    done
    if _tsoc_enumerate_stack_volumes | grep -q .; then
        return 0
    fi
    return 1
}

_tsoc_stop_app_services_for_docker_reset() {
    if [[ "${SETUP_SYSTEMD:-false}" == true ]] \
        && systemctl is-active --quiet tsoc-backend 2>/dev/null; then
        info "Stopping tsoc-backend and tsoc-frontend before Docker reset …"
        systemctl stop tsoc-frontend tsoc-backend 2>/dev/null || true
    elif [[ -f "${INSTALL_DIR}/logs/backend.pid" ]]; then
        stop_application_services 2>/dev/null || true
    fi
}

_reset_tsoc_docker_stack() {
    local compose_file="${INSTALL_DIR}/backend/docker-compose.yml"

    _tsoc_compose_executable || true

    _tsoc_stop_app_services_for_docker_reset

    if [[ -f "$compose_file" ]] && [[ ${#TSOC_COMPOSE_CMD[@]} -gt 0 ]]; then
        info "Removing ThinkingSOC stack via compose down -v (project ${TSOC_COMPOSE_PROJECT_NAME}) …"
        _tsoc_compose_in_backend down -v --remove-orphans \
            || warn "compose down returned non-zero (continuing cleanup)"
    fi

    local c
    for c in "${TSOC_STACK_CONTAINERS[@]}"; do
        if docker ps -a --filter "name=^${c}$" -q 2>/dev/null | grep -q .; then
            info "Removing container ${c} …"
            docker rm -f "$c" 2>/dev/null || true
        fi
    done

    local vol seen="" v
    while read -r vol; do
        [[ -n "$vol" ]] || continue
        if [[ " ${seen} " == *" ${vol} "* ]]; then
            continue
        fi
        seen="${seen} ${vol}"
        info "Removing volume ${vol} …"
        docker volume rm -f "$vol" 2>/dev/null || true
    done < <(_tsoc_enumerate_stack_volumes | sort -u)

    ok "ThinkingSOC Docker containers and data volumes removed (images kept)"
}

prompt_and_reset_tsoc_docker_stack() {
    if ! _tsoc_docker_stack_detected; then
        info "No prior ThinkingSOC Docker stack detected — creating fresh containers and volumes."
        return 0
    fi

    echo ""
    warn "An existing ThinkingSOC Docker stack was detected on this machine."
    echo ""
    echo "  The installer can remove it so demo data and schema load cleanly."
    echo "  This will STOP and DELETE:"
    echo "    · Containers: tsoc-postgres, tsoc-qdrant, tsoc-neo4j"
    echo "    · Data volumes: tsoc_pgdata, tsoc_qdrant_data, tsoc_neo4j_data"
    echo "      (and any legacy backend_tsoc_* volumes from older installs)"
    echo "      (all PostgreSQL, Qdrant, and Neo4j data on this host)"
    echo ""
    echo "  This will NOT delete Docker images (postgres/qdrant/neo4j stay cached)."
    echo "  After cleanup, the stack is started again from local images."
    echo ""

    # A destructive reset must never be the unattended default. CI and
    # operator smoke tests can opt in explicitly, which makes install.sh
    # reproducible without weakening the interactive safety gate.
    case "${TSOC_RESET_EXISTING_STACK:-}" in
        true|1|yes)
            warn "TSOC_RESET_EXISTING_STACK explicitly permits this ThinkingSOC-only reset."
            _reset_tsoc_docker_stack || return 1
            return 0
            ;;
        false|0|no)
            err "Install stopped — TSOC_RESET_EXISTING_STACK explicitly forbids resetting the existing stack."
            return 1
            ;;
    esac

    if ! prompt_yn "Remove existing ThinkingSOC containers and volumes now?" "n"; then
        err "Install stopped — remove the stack manually or answer Yes to continue with a clean Docker reset."
        return 1
    fi

    _reset_tsoc_docker_stack || return 1
    return 0
}

_wait_tsoc_stack_ready() {
    local i
    info "Waiting for PostgreSQL (tsoc-postgres) …"
    for (( i = 1; i <= 30; i++ )); do
        if docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
            ok "PostgreSQL ready"
            break
        fi
        if [[ "$i" -eq 30 ]]; then
            err "PostgreSQL did not become ready in time"
            return 1
        fi
        sleep 2
    done

    info "Waiting for Qdrant (tsoc-qdrant) …"
    for (( i = 1; i <= 30; i++ )); do
        if curl -sf --noproxy '*' http://127.0.0.1:6333/readyz &>/dev/null; then
            ok "Qdrant ready"
            return 0
        fi
        if [[ "$i" -eq 30 ]]; then
            warn "Qdrant not ready yet (install may continue; RAG may backfill later)"
            return 0
        fi
        sleep 2
    done
}

start_tsoc_docker_stack() {
    local compose_file="${INSTALL_DIR}/backend/docker-compose.yml"
    local c running=0

    if ! _tsoc_compose_executable; then
        err "Docker Compose not found (install docker-compose-plugin)"
        return 1
    fi
    if [[ ! -f "$compose_file" ]]; then
        err "Missing ${compose_file}"
        return 1
    fi

    ensure_docker_stack_images || return 1

    for c in "${TSOC_STACK_CONTAINERS[@]}"; do
        if docker ps --filter "name=^${c}$" --filter "status=running" -q 2>/dev/null | grep -q .; then
            running=$((running + 1))
        fi
    done
    if [[ "$running" -eq "${#TSOC_STACK_CONTAINERS[@]}" ]]; then
        ok "ThinkingSOC Docker stack already running"
        _wait_tsoc_stack_ready || return 1
        return 0
    fi

    info "Starting ThinkingSOC Docker stack (project ${TSOC_COMPOSE_PROJECT_NAME}: postgres + qdrant + neo4j) from local images …"
    if ! _tsoc_compose_in_backend up -d; then
        err "docker compose up failed"
        return 1
    fi
    ok "Docker stack started"
    _wait_tsoc_stack_ready || return 1
}

docker_pull_image_retry() {
    local image="$1"
    local attempt max_attempts="${TSOC_DOCKER_PULL_ATTEMPTS:-5}"
    local delay="${TSOC_DOCKER_PULL_DELAY:-5}"

    for (( attempt = 1; attempt <= max_attempts; attempt++ )); do
        if [[ "$attempt" -gt 1 ]]; then
            warn "Retrying docker pull ${image} (${attempt}/${max_attempts}) ..."
            sleep "$delay"
        fi
        info "Pulling Docker image ${image} ..."
        if [[ "$INSTALL_VERBOSE" == true ]]; then
            if docker pull "$image"; then
                ok "Pulled ${image}"
                return 0
            fi
        elif docker pull "$image" >/dev/null 2>&1; then
            ok "Pulled ${image}"
            return 0
        fi
    done

    err "Failed to pull ${image} after ${max_attempts} attempts (Docker Hub network/proxy?)"
    return 1
}

ensure_docker_stack_images() {
    local image missing=0
    for image in "${TSOC_DOCKER_IMAGES[@]}"; do
        if docker image inspect "$image" &>/dev/null; then
            ok "Docker image present: ${image}"
        elif ! docker_pull_image_retry "$image"; then
            missing=$((missing + 1))
        fi
    done
    if [[ "$missing" -gt 0 ]]; then
        err "${missing} Docker image(s) could not be pulled from registry-1.docker.io"
        return 1
    fi
    return 0
}
