#!/usr/bin/env bash

_step_system_update() {
    info "Updating package lists ..."
    apt_update_lists || return 1
    info "Upgrading installed packages ..."
    apt_upgrade_all || return 1
    apt_updated=true
    ok "System updated"
}

_step_prerequisites() {
    if check_all_prerequisites; then
        return 0
    fi
    install_missing_prerequisites
}

_step_python_bootstrap() {
    ensure_python_venv_package || return 1
    ensure_ca_certificates || return 1
}

_step_repository() {
    setup_repo
    if [[ "${LOAD_DEMO_DATA:-false}" == true ]]; then
        sync_demo_snapshot_to_install_dir || true
    fi
}

_step_backend_venv() {
    setup_venv
}

_step_backend_env() {
    setup_backend_env || return 1
}

_step_docker_images() {
    ensure_docker_stack_images
}

_step_prepare_tsoc_docker_stack() {
    prompt_and_reset_tsoc_docker_stack || return 1
    start_tsoc_docker_stack || return 1
}

_step_project_setup() {
    local seed_flag=""
    if [[ "$LOAD_DEMO_DATA" == false ]]; then
        seed_flag="--no-seed"
    elif [[ "${DEMO_SEED_MODE:-}" == "dump" ]]; then
        # Full pg_dump restore runs after setup.py — skip JSON/CSV seed to avoid
        # loading a partial snapshot (rag=0, findings=1) that confuses diagnostics.
        seed_flag="--no-seed"
    fi
    ensure_docker_stack_images || return 1
    if [[ "$LOAD_DEMO_DATA" == true ]]; then
        ensure_demo_data_ready_for_install || return 1
        case "${DEMO_SEED_MODE:-}" in
            dump)
                info "Running project setup (schema only — demo data from full pg_dump backup next) …"
                ;;
            snapshot)
                info "Running project setup (database + moment demo snapshot) …"
                ;;
            csv)
                info "Running project setup (database + demo CSV seed) …"
                ;;
            *)
                info "Running project setup (database + demo seed) …"
                ;;
        esac
    else
        info "Running project setup (database, no demo seed) …"
    fi
    info "Log file: $INSTALL_DIR/setup.log"
    _run_setup_py_once "$seed_flag" || return 1

    if [[ "$LOAD_DEMO_DATA" == true ]]; then
        _apply_demo_snapshot_to_postgres || return 1
        _demo_sync_ingest_token_to_frontend || true
        if [[ -n "${DEMO_RESTORE_LOG:-}" && -f "${DEMO_RESTORE_LOG}" ]]; then
            info "Demo restore log: ${DEMO_RESTORE_LOG}"
        fi
    fi
}

_step_frontend() {
    setup_frontend
}

_step_start_services() {
    if [[ "${SETUP_SYSTEMD:-false}" == true ]]; then
        ok "Services managed by systemd (tsoc-backend, tsoc-frontend)"
        return 0
    fi
    start_application_services
}

_step_frontend_build() {
    ensure_frontend_production_build || return 1
}

_step_embedding_model() {
    ensure_embedding_model_for_install || return 1
}

_step_smoke_test() {
    run_smoke_test
}
