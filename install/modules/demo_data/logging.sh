#!/usr/bin/env bash
# Demo data — diagnostic log file + structured install messages.

_demo_restore_log_init() {
    DEMO_RESTORE_LOG="${INSTALL_DIR}/logs/demo-restore.log"
    mkdir -p "${INSTALL_DIR}/logs"
    {
        echo "================================================================"
        echo "ThinkingSOC demo data restore log"
        echo "started: $(date -Iseconds 2>/dev/null || date)"
        echo "INSTALL_DIR=${INSTALL_DIR}"
        echo "INSTALL_SCRIPT_DIR=${INSTALL_SCRIPT_DIR:-}"
        echo "LOAD_DEMO_DATA=${LOAD_DEMO_DATA:-false}"
        echo "DEMO_SEED_MODE=${DEMO_SEED_MODE:-}"
        echo "FORCE_DEMO_RESTORE=${FORCE_DEMO_RESTORE:-false}"
        echo "hostname=$(hostname 2>/dev/null || echo unknown)"
        echo "================================================================"
    } >> "$DEMO_RESTORE_LOG"
}

# Append arbitrary command output to demo-restore.log (for psql/python tails).
_demo_log_file_tail() {
    local label="$1" path="$2" max_lines="${3:-40}"
    [[ -f "$path" ]] || return 0
    if [[ -n "$DEMO_RESTORE_LOG" ]]; then
        echo "" >> "$DEMO_RESTORE_LOG"
        echo "--- tail ${label} (${path}, last ${max_lines} lines) ---" >> "$DEMO_RESTORE_LOG"
        tail -n "$max_lines" "$path" >> "$DEMO_RESTORE_LOG" 2>/dev/null || true
    fi
}

_demo_log() {
    local line="[$(date -Iseconds 2>/dev/null || date)] $*"
    if [[ -n "$DEMO_RESTORE_LOG" ]]; then
        echo "$line" >> "$DEMO_RESTORE_LOG"
    fi
    info "$*"
}

_demo_log_warn() {
    local line="[$(date -Iseconds 2>/dev/null || date)] WARN: $*"
    if [[ -n "$DEMO_RESTORE_LOG" ]]; then
        echo "$line" >> "$DEMO_RESTORE_LOG"
    fi
    warn "$*"
}

_demo_log_err() {
    local line="[$(date -Iseconds 2>/dev/null || date)] ERROR: $*"
    if [[ -n "$DEMO_RESTORE_LOG" ]]; then
        echo "$line" >> "$DEMO_RESTORE_LOG"
    fi
    err "$*"
}

_demo_log_section() {
    local title="$1"
    if [[ -n "$DEMO_RESTORE_LOG" ]]; then
        echo "" >> "$DEMO_RESTORE_LOG"
        echo "--- ${title} ---" >> "$DEMO_RESTORE_LOG"
    fi
    info "Demo restore: ${title}"
}

_demo_log_file_stat() {
    local label="$1"
    local path="$2"
    if [[ -f "$path" ]]; then
        local size lines
        size="$(du -h "$path" 2>/dev/null | cut -f1 || echo "?")"
        lines="$(wc -l < "$path" 2>/dev/null | tr -d '[:space:]' || echo "?")"
        _demo_log "  ${label}: present path=${path} size=${size} lines=${lines}"
    else
        _demo_log_warn "  ${label}: MISSING path=${path}"
    fi
}

_demo_log_paths_and_sources() {
    _demo_log_section "Demo data paths (pre-restore)"
    _demo_log "  INSTALL_DIR=${INSTALL_DIR}"
    _demo_log "  INSTALL_SCRIPT_DIR=${INSTALL_SCRIPT_DIR:-<unset>}"
    _demo_log "  DEMO_SEED_MODE=${DEMO_SEED_MODE:-<unset>}"
    _demo_log_file_stat "Full backup (primary)" "$(_demo_dump_file)"
    _demo_log_file_stat "Full backup (install script tree)" \
        "${INSTALL_SCRIPT_DIR:-}/backend/data/demo/postgres_dump/tsoc_demo.sql"
    _demo_log_file_stat "JSON manifest" "$(_demo_snapshot_manifest)"
    local f
    for f in "${DEMO_SNAPSHOT_REQUIRED_FILES[@]}"; do
        _demo_log_file_stat "JSON ${f}" "$(_demo_snapshot_dir)/${f}"
    done
    if [[ -f "${INSTALL_DIR}/backend/.env" ]]; then
        local dsn
        dsn="$(grep -E '^TSOC_POSTGRES_DSN=' "${INSTALL_DIR}/backend/.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
        if [[ -n "$dsn" ]]; then
            dsn="${dsn//:*@/:***@}"
            _demo_log "  TSOC_POSTGRES_DSN (from .env)=${dsn}"
        else
            _demo_log_warn "  TSOC_POSTGRES_DSN not set in backend/.env"
        fi
    else
        _demo_log_warn "  backend/.env not found at ${INSTALL_DIR}/backend/.env"
    fi
    if docker ps --filter "name=^tsoc-postgres$" --filter "status=running" -q 2>/dev/null | grep -q .; then
        _demo_log "  tsoc-postgres container: running"
        if docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
            _demo_log "  PostgreSQL pg_isready: OK"
        else
            _demo_log_warn "  PostgreSQL pg_isready: NOT READY"
        fi
    else
        _demo_log_warn "  tsoc-postgres container: not running"
    fi
    if declare -F _demo_log_token_status &>/dev/null 2>&1; then
        _demo_log_token_status
    fi
}

_demo_log_restore_hint() {
    _demo_log "Full diagnostic log: ${DEMO_RESTORE_LOG}"
    _demo_log "UI diagnose: bash ${INSTALL_DIR}/scripts/diagnose-demo-ui.sh"
    _demo_log "Manual restore: sudo bash ${INSTALL_DIR}/scripts/restore-demo-db.sh"
    _demo_log "Force restore on reinstall: FORCE_DEMO_RESTORE=true sudo bash install.sh"
    _demo_log "Re-capture backup: bash ${INSTALL_DIR}/scripts/backup-demo-db.sh (on source machine, then commit + push tsoc_demo.sql)"
}
