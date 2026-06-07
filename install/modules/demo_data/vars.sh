#!/usr/bin/env bash
# Demo data — shared globals and path helpers.

# Set by ensure_demo_data_ready_for_install: dump | snapshot | csv | (empty)
DEMO_SEED_MODE=""

DEMO_RESTORE_LOG=""

# Files required for moment demo (must match export_postgres_snapshot).
DEMO_SNAPSHOT_REQUIRED_FILES=(
    tsoc_users.json
    tsoc_assets.json
    tsoc_relationships.json
    tsoc_identity_rules.json
    tsoc_records.json
    graph_findings.json
)

_demo_snapshot_dir() {
    echo "${INSTALL_DIR}/backend/data/demo/postgres_snapshot"
}

_demo_snapshot_manifest() {
    echo "$(_demo_snapshot_dir)/manifest.json"
}

# Full PostgreSQL backup (pg_dump): primary, most faithful demo source.
_demo_dump_file() {
    echo "${INSTALL_DIR}/backend/data/demo/postgres_dump/tsoc_demo.sql"
}
