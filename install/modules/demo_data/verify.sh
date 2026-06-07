#!/usr/bin/env bash
# Demo data — bundle verification and runtime notes.

demo_data_runtime_note() {
    info "Demo load: Docker PostgreSQL + Python asyncpg (installed by this installer; no extra apt packages)."
}

verify_demo_snapshot_bundle() {
    local missing=0
    local f

    local manifest
    manifest="$(_demo_snapshot_manifest)"
    if [[ ! -f "$manifest" ]]; then
        warn "Demo snapshot manifest not found: ${manifest}"
        warn "Install will fall back to CSV inventory under backend/data/demo/ if present."
        return 1
    fi

    local snap_dir
    snap_dir="$(_demo_snapshot_dir)"
    for f in "${DEMO_SNAPSHOT_REQUIRED_FILES[@]}"; do
        if [[ ! -f "${snap_dir}/${f}" ]]; then
            err "Missing demo snapshot file: ${snap_dir}/${f}"
            missing=$((missing + 1))
        fi
    done

    if [[ "$missing" -gt 0 ]]; then
        err "Incomplete demo snapshot bundle (${missing} file(s) missing)."
        return 1
    fi

    ok "Demo snapshot bundle OK (${snap_dir})"
    return 0
}
