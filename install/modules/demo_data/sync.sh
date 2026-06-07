#!/usr/bin/env bash
# Demo data — copy bundled dump/snapshot into INSTALL_DIR when paths differ.

_sync_demo_dump_to_install_dir() {
    local src_dump="${INSTALL_SCRIPT_DIR:-}/backend/data/demo/postgres_dump/tsoc_demo.sql"
    local dest_dump dest_dir
    dest_dump="$(_demo_dump_file)"
    dest_dir="$(dirname "$dest_dump")"

    if [[ -f "$dest_dump" ]]; then
        local mtime size
        mtime="$(stat -c '%y' "$dest_dump" 2>/dev/null | cut -d. -f1 || echo '?')"
        size="$(du -h "$dest_dump" 2>/dev/null | cut -f1 || echo '?')"
        _demo_log "  dump sync: dest already exists — skip copy (${dest_dump})"
        _demo_log "  dump sync: existing file mtime=${mtime} size=${size} (git pull updates this file in place)"
        return 0
    fi
    if [[ ! -f "$src_dump" ]]; then
        _demo_log_warn "  dump sync: source missing — ${src_dump}"
        return 1
    fi
    if [[ "$(readlink -f "$src_dump" 2>/dev/null || echo "$src_dump")" == "$(readlink -f "$dest_dump" 2>/dev/null || echo "$dest_dump")" ]]; then
        _demo_log "  dump sync: same path — skip"
        return 0
    fi

    info "Copying demo database backup into install tree …"
    mkdir -p "$dest_dir"
    cp -a "$src_dump" "$dest_dump" || return 1
    ok "Demo database backup copied to ${dest_dump}"
    _demo_log "  dump sync: copied ${src_dump} → ${dest_dump}"
    return 0
}

# Copy bundled demo data into the install tree when install dir differs from the
# checkout that launched install.sh (otherwise no-op: clone == install dir).
sync_demo_snapshot_to_install_dir() {
    _sync_demo_dump_to_install_dir || true

    local src_dir="${INSTALL_SCRIPT_DIR:-}/backend/data/demo/postgres_snapshot"
    local src_manifest="${src_dir}/manifest.json"
    local dest_dir dest_manifest

    dest_dir="$(_demo_snapshot_dir)"
    dest_manifest="$(_demo_snapshot_manifest)"

    if [[ -f "$dest_manifest" ]]; then
        _demo_log "  snapshot sync: manifest already exists — skip (${dest_manifest})"
        return 0
    fi
    if [[ ! -f "$src_manifest" ]]; then
        return 1
    fi
    if [[ "$(readlink -f "$src_dir" 2>/dev/null || echo "$src_dir")" == "$(readlink -f "$dest_dir" 2>/dev/null || echo "$dest_dir")" ]]; then
        return 1
    fi

    info "Copying demo snapshot into install tree …"
    mkdir -p "$dest_dir"
    cp -a "${src_dir}/." "$dest_dir/" || return 1
    ok "Demo snapshot copied to ${dest_dir}"
    return 0
}
