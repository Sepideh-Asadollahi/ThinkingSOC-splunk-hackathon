"""Persist JSON records to PostgreSQL for TSOC analysis and audit."""

from __future__ import annotations

from . import pg
from .persist import (
    persist_admin_org_gap_to_splunk,
    persist_agentic_ops_route_to_splunk,
    persist_analysis_batch_summary_to_splunk,
    persist_enrichment_to_splunk,
    persist_llm_chat_audit_to_splunk,
    persist_observability_analysis_to_splunk,
    persist_soc_analysis_audit,
    persist_soc_analysis_to_splunk,
    persist_soc_investigation_phases,
    persist_splunk_ingest_summary,
)
from .pg import (
    close_store,
    ensure_pool,
    init_store,
    jsonb_param,
    splunk_store_configured,
    submit_hec_event,
)
from .query import get_stored_event_by_id, search_stored_events

# Backward-compatible alias used in tests
_jsonb_param = jsonb_param


def __getattr__(name: str):
    if name == "_PG_POOL":
        return pg._PG_POOL
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "_PG_POOL",
    "_jsonb_param",
    "close_store",
    "ensure_pool",
    "init_store",
    "jsonb_param",
    "persist_admin_org_gap_to_splunk",
    "persist_agentic_ops_route_to_splunk",
    "persist_analysis_batch_summary_to_splunk",
    "persist_enrichment_to_splunk",
    "persist_llm_chat_audit_to_splunk",
    "persist_observability_analysis_to_splunk",
    "persist_soc_analysis_audit",
    "persist_soc_analysis_to_splunk",
    "persist_soc_investigation_phases",
    "persist_splunk_ingest_summary",
    "get_stored_event_by_id",
    "search_stored_events",
    "splunk_store_configured",
    "submit_hec_event",
]
