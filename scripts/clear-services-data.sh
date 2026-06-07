#!/usr/bin/env bash
# Clear Analysis + Correlation demo data from PostgreSQL and Neo4j.
# Keeps: inventory (users/assets/relationships), splunk_ingest, SOC chat, identity rules.
#
# Usage: bash scripts/clear-services-data.sh [--yes]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

AUTO_YES=false
[[ "${1:-}" == "--yes" || "${1:-}" == "-y" ]] && AUTO_YES=true

# tsoc_records types for Analysis pipeline + investigation shards
ANALYSIS_RECORD_TYPES=(
    soc_analysis
    soc_analysis_audit
    soc_analysis_batch
    observability_analysis
    agentic_ops_analysis
    soc_investigation_summary
    soc_investigation_evidence_chain
    soc_investigation_hunter
    soc_investigation_judge
    soc_investigation_defender
    investigation_analyst_action
    admin_org_gap_suggest
    enrichment_resolve
)

# tsoc_rag_documents doc_types for Services (Analysis + Correlation RAG index)
SERVICES_RAG_DOC_TYPES=(
    soc_analysis
    observability_analysis
    correlation_finding
    correlation_alert
    correlation_attack_path
)

log() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*" >&2; }

if ! docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
    echo "[ERROR] tsoc-postgres not ready" >&2
    exit 1
fi

log "Current Services-related counts (before clear):"
docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc \
    "SELECT 'analyses='||COUNT(*)::text FROM tsoc_records
       WHERE tsoc_record_type IN ('soc_analysis','observability_analysis')
     UNION ALL SELECT 'graph_findings='||COUNT(*)::text FROM graph_findings
     UNION ALL SELECT 'services_rag='||COUNT(*)::text FROM tsoc_rag_documents
       WHERE doc_type IN ('soc_analysis','observability_analysis','correlation_finding','correlation_alert','correlation_attack_path');" \
    2>/dev/null | grep -viE 'WARNING|NOTICE' | sed 's/^/  /'

log "tsoc_records by type (rows that will be removed if present):"
types_sql="$(printf "'%s'," "${ANALYSIS_RECORD_TYPES[@]}")"
types_sql="${types_sql%,}"
docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc \
    "SELECT tsoc_record_type||'='||COUNT(*)::text FROM tsoc_records
     WHERE tsoc_record_type IN (${types_sql})
     GROUP BY 1 ORDER BY 1;" 2>/dev/null | grep -viE 'WARNING|NOTICE' | sed 's/^/  /' || true

if [[ "$AUTO_YES" != true ]]; then
    echo ""
    echo "This will DELETE Analysis + Correlation data from PostgreSQL and Neo4j."
    echo "Inventory (users/assets/relationships) and splunk_ingest rows are kept."
    read -r -p "Continue? [y/N] " ans
    [[ "${ans,,}" == "y" || "${ans,,}" == "yes" ]] || { echo "Aborted."; exit 0; }
fi

# Stop app so no open connections hold stale reads
if systemctl is-active --quiet tsoc-backend 2>/dev/null; then
    log "Stopping tsoc-backend briefly …"
    systemctl stop tsoc-backend 2>/dev/null || true
    RESTART_BACKEND=true
else
    RESTART_BACKEND=false
fi

log "Clearing PostgreSQL …"
types_in="$(printf "'%s'," "${ANALYSIS_RECORD_TYPES[@]}")"
types_in="${types_in%,}"
rag_in="$(printf "'%s'," "${SERVICES_RAG_DOC_TYPES[@]}")"
rag_in="${rag_in%,}"

docker exec -i tsoc-postgres psql -U tsoc -d tsoc -v ON_ERROR_STOP=1 -q <<SQL
DELETE FROM tsoc_records WHERE tsoc_record_type IN (${types_in});
TRUNCATE TABLE graph_findings;
DELETE FROM tsoc_rag_documents WHERE doc_type IN (${rag_in});
SELECT setval(
  pg_get_serial_sequence('tsoc_records', 'id'),
  COALESCE((SELECT MAX(id) FROM tsoc_records), 1),
  (SELECT COUNT(*) > 0 FROM tsoc_records)
);
SQL

log "Clearing Neo4j graph (alerts, entities, correlation edges) …"
if docker ps --filter "name=^tsoc-neo4j$" --filter "status=running" -q 2>/dev/null | grep -q .; then
    docker exec tsoc-neo4j cypher-shell -u neo4j -p tsoc-tsoc \
        "MATCH (n) DETACH DELETE n;" 2>/dev/null \
        && log "Neo4j: all nodes removed" \
        || warn "Neo4j clear failed (check NEO4J_PASSWORD)"
else
    warn "tsoc-neo4j not running — skipped graph clear"
fi

log "Re-seeding correlation demo baseline (Operation Shadow Login) …"
if bash "${REPO_ROOT}/scripts/seed-correlation-demo.sh"; then
    log "Correlation demo baseline ready — Attack Discovery can run immediately."
else
    warn "Correlation demo seed failed — restart backend or run: bash scripts/seed-correlation-demo.sh"
fi

log "Counts after clear:"
docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc \
    "SELECT 'analyses='||COUNT(*)::text FROM tsoc_records
       WHERE tsoc_record_type IN ('soc_analysis','observability_analysis')
     UNION ALL SELECT 'graph_findings='||COUNT(*)::text FROM graph_findings
     UNION ALL SELECT 'services_rag='||COUNT(*)::text FROM tsoc_rag_documents
       WHERE doc_type IN ('soc_analysis','observability_analysis','correlation_finding','correlation_alert','correlation_attack_path')
     UNION ALL SELECT 'inventory_users='||COUNT(*)::text FROM tsoc_users
     UNION ALL SELECT 'inventory_assets='||COUNT(*)::text FROM tsoc_assets;" \
    2>/dev/null | grep -viE 'WARNING|NOTICE' | sed 's/^/  /'

if [[ "$RESTART_BACKEND" == true ]]; then
    log "Restarting tsoc-backend …"
    systemctl start tsoc-backend 2>/dev/null || true
fi

log "Done. Analysis/RAG cleared; correlation demo baseline re-seeded (findings + Neo4j alerts)."
log "Optional: bash scripts/backup-demo-db.sh after you generate new demo data."
