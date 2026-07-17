#!/usr/bin/env bash
# Full demo snapshot (backend/data/demo/postgres_snapshot) — loader for install/modules/demo_data/*.sh
#
# Submodules (load order):
#   vars.sh            DEMO_SEED_MODE, path helpers, required JSON file list
#   logging.sh         demo-restore.log + structured install messages
#   diagnostics.sh     token/service/bundle audit, UI proxy probe
#   postgres.sh        row counts, bundle-complete check, restore prep
#   api_check.sh       ingest token sync + triage/graph API visibility
#   sync.sh            copy dump/snapshot into INSTALL_DIR when paths differ
#   verify.sh          bundle verification, runtime note
#   restore_dump.sh    full pg_dump restore via psql
#   restore_snapshot.sh JSON snapshot fallback (Python asyncpg)
#   apply.sh           orchestrate dump → snapshot fallback
#   steps.sh           ensure_demo_data_ready_for_install, post-services step

_DEMO_MODULE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/demo_data" && pwd)"

_demo_require_submodule() {
    local path="$1"
    if [[ ! -f "$path" ]]; then
        echo "[ERROR] Missing demo-data module: $path" >&2
        exit 1
    fi
}

_demo_load_submodules() {
    local name path
    local -a modules=(
        vars
        logging
        diagnostics
        postgres
        api_check
        sync
        verify
        restore_dump
        restore_snapshot
        apply
        steps
    )
    for name in "${modules[@]}"; do
        path="${_DEMO_MODULE_DIR}/${name}.sh"
        _demo_require_submodule "$path"
        # shellcheck disable=SC1090
        source "$path"
    done
}

_demo_load_submodules
