#!/usr/bin/env bash
# Demo data — full pg_dump restore via psql.

# Restore the full demo backup with psql. Returns: 0 ok, 1 failed, 2 no dump.
_restore_demo_dump_to_postgres() {
    local dump psql_log rc t0 t1 elapsed_sec
    dump="$(_demo_dump_file)"
    if [[ ! -f "$dump" ]]; then
        _demo_log "  pg_dump restore: skipped — backup file not found (${dump})"
        return 2
    fi

    if ! docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
        _demo_log_err "tsoc-postgres is not ready — cannot restore demo backup"
        return 1
    fi

    _demo_log_section "Restore: full pg_dump backup (psql)"

    if declare -F _demo_log_bundle_complete_audit &>/dev/null 2>&1; then
        _demo_log_bundle_complete_audit || true
    fi

    if [[ "${FORCE_DEMO_RESTORE:-false}" != true ]] && _demo_db_bundle_complete; then
        _demo_log "  pg_dump restore: skipped — demo bundle already complete (avoid re-running DROP on live DB)"
        _demo_log "  Tip: FORCE_DEMO_RESTORE=true or: sudo bash scripts/restore-demo-db.sh"
        _demo_log_postgres_counts "Row counts (restore not needed)"
        _demo_log_record_type_breakdown || true
        return 0
    fi
    if [[ "${FORCE_DEMO_RESTORE:-false}" == true ]]; then
        _demo_log "  FORCE_DEMO_RESTORE=true — restoring even though DB may already have data"
    fi

    _demo_log "  dump=${dump}"
    _demo_log "  command: docker exec -i tsoc-postgres psql -U tsoc -d tsoc -v ON_ERROR_STOP=1 -q < ${dump}"
    psql_log="${INSTALL_DIR}/logs/demo-restore-psql.log"

    _demo_stop_app_for_db_restore
    if declare -F _demo_log_pg_activity &>/dev/null 2>&1; then
        _demo_log_pg_activity
    fi
    _demo_pg_terminate_other_sessions
    if declare -F _demo_log_pg_activity &>/dev/null 2>&1; then
        _demo_log "  PostgreSQL sessions after terminate:"
        _demo_log_pg_activity
    fi
    _demo_log_postgres_counts "Row counts BEFORE restore" || true
    _demo_log_record_type_breakdown || true

    t0=$(date +%s)
    info "Restoring full demo database from backup (psql) …"
    if docker exec -i tsoc-postgres psql -U tsoc -d tsoc -v ON_ERROR_STOP=1 -q < "$dump" >"$psql_log" 2>&1; then
        rc=0
    else
        rc=$?
    fi
    t1=$(date +%s)
    elapsed_sec=$((t1 - t0))

    if [[ "$rc" -ne 0 ]]; then
        _demo_log_err "Demo database restore failed (exit=${rc}, duration=${elapsed_sec}s) — see ${psql_log}"
        _demo_log_err "Common causes: backend held DB connections during DROP; dump file corrupt; schema conflict"
        _demo_log_file_tail "psql stderr/stdout" "$psql_log" 50
        err "Demo database restore failed (${dump}) — details: ${psql_log} and ${DEMO_RESTORE_LOG}"
        return 1
    fi

    _demo_log "  psql restore: exit=0 duration=${elapsed_sec}s (verbose: ${psql_log})"
    local err_lines
    err_lines="$(grep -ciE '^ERROR:|^FATAL:' "$psql_log" 2>/dev/null || echo 0)"
    if [[ "${err_lines:-0}" -gt 0 ]]; then
        _demo_log_warn "  psql log contains ${err_lines} ERROR/FATAL line(s) despite exit=0 — review ${psql_log}"
        _demo_log_file_tail "psql errors" "$psql_log" 20
    fi
    ok "Demo database restored from backup"
    _demo_log_postgres_counts "Row counts AFTER restore (dump path)"
    _demo_log_record_type_breakdown || true
    _demo_log_api_visibility "API check after dump restore (backend may not be up yet)"
    return 0
}
