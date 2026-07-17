#!/usr/bin/env bash
# Demo data — install-step entry points (pre-flight, post-services).

ensure_demo_data_ready_for_install() {
    DEMO_SEED_MODE=""

    if [[ "${LOAD_DEMO_DATA:-false}" != true ]]; then
        return 0
    fi

    _demo_restore_log_init
    demo_data_runtime_note
    if declare -F _demo_log_runtime_context &>/dev/null 2>&1; then
        _demo_log_runtime_context
    fi
    _demo_log_section "Pre-flight: sync bundled demo files into INSTALL_DIR"
    sync_demo_snapshot_to_install_dir || _demo_log_warn "sync_demo_snapshot_to_install_dir returned non-zero (may be OK if INSTALL_DIR == clone)"

    if [[ -f "$(_demo_dump_file)" ]]; then
        DEMO_SEED_MODE="dump"
        _demo_log_paths_and_sources
        ok "Demo database backup found ($(_demo_dump_file))"
        _demo_log "Selected restore mode: dump (full pg_dump backup via psql)"
        return 0
    fi

    if verify_demo_snapshot_bundle; then
        DEMO_SEED_MODE="snapshot"
        _demo_log_paths_and_sources
        _demo_log "Selected restore mode: snapshot (full JSON fallback via Python asyncpg)"
        _demo_log_warn "Full SQL backup missing — using the full JSON snapshot fallback"
        return 0
    fi

    if [[ -d "${INSTALL_DIR}/backend/data/demo" ]] && compgen -G "${INSTALL_DIR}/backend/data/demo/tsoc_users.csv" >/dev/null; then
        DEMO_SEED_MODE="csv"
        _demo_log_paths_and_sources
        _demo_log_warn "Selected restore mode: csv (inventory only — no tsoc_records / graph_findings)"
        return 0
    fi

    _demo_log_paths_and_sources
    err "Load demo data was requested but no demo files found under ${INSTALL_DIR}/backend/data/demo/"
    err "Ensure the repository includes backend/data/demo/postgres_dump/tsoc_demo.sql or postgres_snapshot/ JSON files."
    err "If you use git clone, commit and push demo files first. See: ${DEMO_RESTORE_LOG}"
    return 1
}

_tsoc_services_running_for_install() {
    if [[ "${SETUP_SYSTEMD:-false}" == true ]]; then
        systemctl is-active --quiet tsoc-backend 2>/dev/null \
            && systemctl is-active --quiet tsoc-frontend 2>/dev/null
        return $?
    fi
    _tsoc_tcp_port_in_use 9876 2>/dev/null && _tsoc_tcp_port_in_use 3000 2>/dev/null
}

# After services are running: verify demo DB, restore only if incomplete, then restart API/UI.
_step_apply_demo_and_restart_services() {
    [[ "${LOAD_DEMO_DATA:-false}" == true ]] || return 0

    [[ -n "$DEMO_RESTORE_LOG" ]] || _demo_restore_log_init
    _demo_log_section "Demo-load install step (post-services)"

    sync_demo_snapshot_to_install_dir || _demo_log_warn "sync skipped or failed in demo-load step"

    if [[ "${FORCE_DEMO_RESTORE:-false}" != true ]] && _demo_db_bundle_complete; then
        _demo_log "Demo bundle already complete — skipping second pg_dump restore (project-setup already loaded data)"
        _demo_log "  Tip: FORCE_DEMO_RESTORE=true or: sudo bash scripts/restore-demo-db.sh"
        _demo_log_postgres_counts "Row counts (demo-load verify only)"
    elif ! _apply_demo_snapshot_to_postgres; then
        _demo_log_err "Demo-load step failed — UI may show empty Analysis/Correlation pages"
        _demo_log_restore_hint
        return 1
    fi

    if [[ -x "${INSTALL_DIR}/scripts/seed-correlation-demo.sh" ]]; then
        _demo_log "Ensuring Neo4j correlation graph matches Postgres demo …"
        if bash "${INSTALL_DIR}/scripts/seed-correlation-demo.sh" >>"${DEMO_RESTORE_LOG}" 2>&1; then
            _demo_log "Correlation demo baseline ready (Neo4j + graph_findings)."
        else
            _demo_log_warn "Correlation demo seed failed — backend startup will retry automatically"
        fi
    fi

    _demo_sync_ingest_token_to_frontend || true

    if ! _tsoc_services_running_for_install; then
        _demo_log "Services not running yet — demo data is in PostgreSQL; will appear after first start"
        _demo_log_postgres_counts "Final row counts (services not restarted yet)"
        _demo_log_restore_hint
        return 0
    fi

    info "Restarting backend and frontend so the UI loads demo data …"
    _demo_log "Restarting tsoc-backend + tsoc-frontend after demo restore …"
    if _pc_restart_tsoc_services_for_env; then
        ok "Services restarted with demo data active"
        _demo_log "Service restart: OK"
    else
        warn "Automatic restart after demo load did not verify — retrying once …"
        _demo_log_warn "Service restart: first attempt did not verify — retrying"
        sleep 3
        if _pc_restart_tsoc_services_for_env; then
            _demo_log "Service restart: OK on retry"
        else
            _demo_log_warn "Service restart: failed after retry — UI may show stale/empty data until manual restart"
        fi
    fi

    _demo_log_postgres_counts "Final row counts (after demo-load step)"
    _demo_log_api_visibility "API check after demo-load (post-restart)"
    if declare -F _demo_log_full_diagnostics &>/dev/null 2>&1; then
        _demo_log_full_diagnostics "Post-install diagnostic summary"
    fi
    if curl -sf --noproxy '*' http://127.0.0.1:9876/health &>/dev/null; then
        _demo_log "  backend /health: OK"
    else
        _demo_log_warn "  backend /health: not responding (embedding may still be loading)"
    fi
    _demo_log_restore_hint
    return 0
}
