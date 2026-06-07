"""Domain vocabulary for LLM prompts (not runtime routing — no hardcoded SQL paths)."""

SOC_USER_VOCABULARY = """
## What the analyst means (they do NOT know table names)

| They say | You should query | Same as UI |
|----------|------------------|------------|
| "how many alerts in SOC", "alerts available", "list alerts" | tsoc_records analyses (soc_analysis + observability_analysis) | Analysis page (/analysis) |
| "high priority", "which are high", "critical items" (on that list) | tsoc_records + investigation_priority in payload triage (see schema) | Analysis page priority column — NOT Splunk normalized.severity |
| "security alerts" / security track | tsoc_records WHERE tsoc_record_type = 'soc_analysis' | Analysis → Security tab |
| "indexed Splunk alerts", "RAG alerts" | tsoc_rag_documents WHERE doc_type = 'splunk_alert' | Chat vector index only |
| "ingested alerts", "raw Splunk rows" | tsoc_records WHERE tsoc_record_type = 'splunk_ingest' | Storage ingest |
| "how many users", "list user names" | tsoc_users | CMDB inventory |
| "how many assets", "list assets" | tsoc_assets | CMDB inventory |
| "correlation findings", "attack discovery", "highest risk findings" | graph_findings | Correlation UI (/correlation) |
| "correlated alerts in graph", "attack path" (narrative) | use RAG (correlation_* doc types), not SQL | Correlation explorer |

**Default:** vague "alerts in SOC" → Analysis page (tsoc_records analyses), NOT splunk_alert unless they say indexed/RAG.
**Correlation:** "findings" with risk_score → graph_findings. Do NOT use tsoc_records soc_analysis for correlation findings.
""".strip()
