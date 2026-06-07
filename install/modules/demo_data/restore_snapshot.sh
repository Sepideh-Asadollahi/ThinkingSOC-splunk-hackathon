#!/usr/bin/env bash
# Demo data — JSON snapshot restore via Python asyncpg.

# Returns: 0 ok, 1 failed, 2 no manifest / nothing to restore.
_restore_demo_json_snapshot_to_postgres() {
    local manifest
    manifest="$(_demo_snapshot_manifest)"
    if [[ ! -f "$manifest" ]]; then
        _demo_log_warn "JSON snapshot manifest missing — no demo restore performed (${manifest})"
        _demo_log_postgres_counts "Row counts (nothing restored)"
        return 2
    fi

    local venv_python="${VENV_PYTHON:-$INSTALL_DIR/backend/.venv/bin/python}"
    if [[ ! -x "$venv_python" ]]; then
        _demo_log_err "Cannot apply demo snapshot — missing $venv_python"
        return 1
    fi

    _demo_log_section "Restore: JSON snapshot (Python apply_postgres_demo_bundle)"
    _demo_log "  manifest=${manifest}"
    _demo_log_postgres_counts "Row counts BEFORE JSON snapshot restore"

    local py_log="${INSTALL_DIR}/logs/demo-restore-python.log"
    info "Applying moment demo snapshot to PostgreSQL …"
    if ! (cd "$INSTALL_DIR/backend" && "$venv_python" - 2>"$py_log" <<'PY'
import asyncio
import os
import sys
import traceback

from dotenv import load_dotenv

load_dotenv(".env", override=True)
sys.path.insert(0, os.getcwd())

async def main() -> None:
    from config import get_settings
    from services.demo.postgres_snapshot import apply_postgres_demo_bundle
    import services.splunk_json_store.pg as pg_mod

    pg_mod._PG_POOL = None
    settings = get_settings()
    dsn = (settings.tsoc_postgres_dsn or "").strip()
    if not dsn:
        raise SystemExit("TSOC_POSTGRES_DSN is not set")
    print(f"[demo-restore] DSN={dsn.split('@')[-1] if '@' in dsn else dsn}", flush=True)
    ok = await apply_postgres_demo_bundle(settings, allow_reseed=True)
    print(f"[demo-restore] apply_postgres_demo_bundle returned {ok}", flush=True)
    if not ok:
        raise SystemExit("apply_postgres_demo_bundle returned False")

asyncio.run(main())
PY
    ); then
        _demo_log_err "Failed to apply demo snapshot — see ${py_log}"
        _demo_log_file_tail "python restore stderr" "$py_log" 40
        err "Failed to apply demo snapshot — details: ${py_log} and ${DEMO_RESTORE_LOG}"
        return 1
    fi

    if [[ -f "$py_log" ]]; then
        _demo_log "  Python restore log: ${py_log}"
        grep -E '^\[demo-restore\]|postgres_snapshot' "$py_log" >> "$DEMO_RESTORE_LOG" 2>/dev/null \
            || _demo_log_file_tail "python restore output" "$py_log" 30
    fi
    ok "Demo snapshot applied to PostgreSQL"
    _demo_log_postgres_counts "Row counts AFTER JSON snapshot restore"
    _demo_log_record_type_breakdown || true
    return 0
}
