#!/usr/bin/env bash
# Demo data — PostgreSQL queries, restore prep, row-count diagnostics.

_demo_query_postgres_counts() {
    if ! docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
        return 1
    fi
    docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc \
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='tsoc_users') AS has_users;
         SELECT CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='tsoc_users')
                THEN (SELECT COUNT(*)::text FROM tsoc_users) ELSE NULL END;
         SELECT CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='tsoc_records')
                THEN (SELECT COUNT(*)::text FROM tsoc_records WHERE tsoc_record_type IN ('soc_analysis','observability_analysis')) ELSE NULL END;
         SELECT CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='graph_findings')
                THEN (SELECT COUNT(*)::text FROM graph_findings) ELSE NULL END;
         SELECT CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='tsoc_rag_documents')
                THEN (SELECT COUNT(*)::text FROM tsoc_rag_documents) ELSE NULL END;
         SELECT CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='tsoc_records')
                THEN (SELECT COUNT(*)::text FROM tsoc_records WHERE payload->>'demo_scenario_id'='judge-tour-runbook-v1') ELSE NULL END;
         SELECT CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='tsoc_chat_messages')
                THEN (SELECT COUNT(*)::text FROM tsoc_chat_messages WHERE conversation_id='demo-runbook-judge-tour-v1') ELSE NULL END;" 2>/dev/null \
        | grep -viE 'WARNING|NOTICE' || true
}

# Full bundle is complete only when baseline data and the linked Runbook judge tour exist.
_demo_db_bundle_complete() {
    local lines has_users users analyses findings rag judge_records judge_chat
    lines="$(_demo_query_postgres_counts)" || return 1
    has_users="$(echo "$lines" | sed -n '1p' | tr -d '[:space:]')"
    users="$(echo "$lines" | sed -n '2p' | tr -d '[:space:]')"
    analyses="$(echo "$lines" | sed -n '3p' | tr -d '[:space:]')"
    findings="$(echo "$lines" | sed -n '4p' | tr -d '[:space:]')"
    rag="$(echo "$lines" | sed -n '5p' | tr -d '[:space:]')"
    judge_records="$(echo "$lines" | sed -n '6p' | tr -d '[:space:]')"
    judge_chat="$(echo "$lines" | sed -n '7p' | tr -d '[:space:]')"

    [[ "$has_users" == "t" ]] || return 1
    [[ -n "$users" && "$users" -ge 7 ]] 2>/dev/null || return 1
    [[ -n "$analyses" && "$analyses" -ge 1 ]] 2>/dev/null || return 1
    [[ -n "$findings" && "$findings" -ge 1 ]] 2>/dev/null || return 1
    [[ -n "$rag" && "$rag" -ge 1 ]] 2>/dev/null || return 1
    [[ -n "$judge_records" && "$judge_records" -ge 10 ]] 2>/dev/null || return 1
    [[ -n "$judge_chat" && "$judge_chat" -ge 2 ]] 2>/dev/null || return 1
    return 0
}

_demo_stop_app_for_db_restore() {
    _demo_log "  Stopping application services so PostgreSQL can DROP/CREATE tables …"
    if [[ "${SETUP_SYSTEMD:-false}" == true ]]; then
        if systemctl is-active --quiet tsoc-backend 2>/dev/null \
            || systemctl is-active --quiet tsoc-frontend 2>/dev/null; then
            systemctl stop tsoc-frontend tsoc-backend 2>/dev/null || true
            _demo_log "  Stopped tsoc-backend + tsoc-frontend (systemd)"
        fi
    elif [[ -f "${INSTALL_DIR}/logs/backend.pid" ]]; then
        stop_application_services 2>/dev/null || true
        _demo_log "  Stopped background backend/frontend processes"
    fi
    sleep 2
}

_demo_pg_terminate_other_sessions() {
    _demo_log "  Terminating other sessions on database tsoc …"
    docker exec tsoc-postgres psql -U tsoc -d tsoc -q -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'tsoc' AND pid <> pg_backend_pid();" \
        2>/dev/null || true
    sleep 1
}

_demo_log_postgres_counts() {
    local label="${1:-PostgreSQL row counts}"
    if ! docker exec tsoc-postgres pg_isready -U tsoc -d tsoc &>/dev/null; then
        _demo_log_warn "${label}: cannot query — PostgreSQL not ready"
        return 1
    fi
    _demo_log_section "${label}"
    local sql out
    sql="SELECT 'tsoc_users='||COUNT(*)::text FROM tsoc_users
         UNION ALL SELECT 'tsoc_assets='||COUNT(*)::text FROM tsoc_assets
         UNION ALL SELECT 'tsoc_relationships='||COUNT(*)::text FROM tsoc_relationships
         UNION ALL SELECT 'tsoc_identity_rules='||COUNT(*)::text FROM tsoc_identity_rules
         UNION ALL SELECT 'tsoc_records='||COUNT(*)::text FROM tsoc_records
         UNION ALL SELECT 'analyses='||COUNT(*)::text FROM tsoc_records
           WHERE tsoc_record_type IN ('soc_analysis','observability_analysis')
         UNION ALL SELECT 'graph_findings='||COUNT(*)::text FROM graph_findings
         UNION ALL SELECT 'tsoc_rag_documents='||COUNT(*)::text FROM tsoc_rag_documents;"
    sql="${sql%;}
         UNION ALL SELECT 'tsoc_chat_conversations='||COUNT(*)::text FROM tsoc_chat_conversations
         UNION ALL SELECT 'tsoc_chat_messages='||COUNT(*)::text FROM tsoc_chat_messages
         UNION ALL SELECT 'runbook_judge_records='||COUNT(*)::text FROM tsoc_records
           WHERE payload->>'demo_scenario_id'='judge-tour-runbook-v1'
         UNION ALL SELECT 'runbook_judge_rag='||COUNT(*)::text FROM tsoc_rag_documents
           WHERE search_name='Judge Demo: Suspicious OAuth Token Replay';"
    out="$(docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc "$sql" 2>&1 || true)"
    out="$(echo "$out" | grep -viE 'WARNING|NOTICE' || true)"
    if echo "$out" | grep -qiE 'does not exist|ERROR:'; then
        _demo_log_warn "  (schema empty or mid-restore — tables not ready for counts yet)"
        while IFS= read -r line; do
            [[ -n "$line" ]] || continue
            _demo_log "  ${line}"
        done <<< "$out"
        return 1
    fi
    if [[ -z "$out" ]]; then
        _demo_log_warn "${label}: query returned empty (tables may not exist yet)"
        return 1
    fi
    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        _demo_log "  ${line}"
    done <<< "$out"
    local analyses findings judge_records judge_rag
    analyses="$(echo "$out" | grep '^analyses=' | cut -d= -f2 | tr -d '[:space:]' || echo 0)"
    findings="$(echo "$out" | grep '^graph_findings=' | cut -d= -f2 | tr -d '[:space:]' || echo 0)"
    judge_records="$(echo "$out" | grep '^runbook_judge_records=' | cut -d= -f2 | tr -d '[:space:]' || echo 0)"
    judge_rag="$(echo "$out" | grep '^runbook_judge_rag=' | cut -d= -f2 | tr -d '[:space:]' || echo 0)"
    if [[ "${analyses:-0}" -lt 1 ]]; then
        _demo_log_warn "  Analysis page (/analysis) will be EMPTY — analyses=${analyses:-0}"
        _demo_log_warn "  Fix: commit backend/data/demo/postgres_dump/tsoc_demo.sql and re-run install, or run: bash scripts/backup-demo-db.sh"
    fi
    if [[ "${findings:-0}" -lt 1 ]]; then
        _demo_log_warn "  Correlation page (/correlation) will be EMPTY — graph_findings=${findings:-0}"
    fi
    if [[ "${judge_records:-0}" -lt 10 || "${judge_rag:-0}" -lt 9 ]]; then
        _demo_log_warn "  Runbook judge tour is INCOMPLETE — records=${judge_records:-0}/10 rag=${judge_rag:-0}/9"
    fi
    if [[ "${analyses:-0}" -ge 1 && "${findings:-0}" -ge 1 ]]; then
        local rag_count
        rag_count="$(echo "$out" | grep '^tsoc_rag_documents=' | cut -d= -f2 | tr -d '[:space:]' || echo 0)"
        _demo_log "  Demo data OK for UI: analyses=${analyses} graph_findings=${findings} rag=${rag_count}"
    fi
    return 0
}
