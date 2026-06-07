#!/usr/bin/env bash
# Demo data — orchestrate pg_dump restore with JSON snapshot fallback.

_apply_demo_snapshot_to_postgres() {
    [[ -n "$DEMO_RESTORE_LOG" ]] || _demo_restore_log_init

    _demo_log_section "Apply demo data to PostgreSQL (mode=${DEMO_SEED_MODE:-unknown})"
    _demo_log_paths_and_sources

    # Primary path: full pg_dump backup (records + RAG + correlation findings,
    # identical to the source server). Falls back to JSON snapshot if absent.
    _restore_demo_dump_to_postgres
    local dump_rc=$?
    case "$dump_rc" in
        0)
            _demo_log "Restore complete via pg_dump backup"
            _demo_log_restore_hint
            return 0
            ;;
        1)
            _demo_log_restore_hint
            return 1
            ;;
        2)
            _demo_log_warn "pg_dump backup absent — trying JSON snapshot fallback"
            ;;
    esac

    _restore_demo_json_snapshot_to_postgres
    local snap_rc=$?
    case "$snap_rc" in
        0)
            _demo_log_restore_hint
            return 0
            ;;
        2)
            _demo_log_restore_hint
            return 0
            ;;
        *)
            _demo_log_restore_hint
            return 1
            ;;
    esac
}
