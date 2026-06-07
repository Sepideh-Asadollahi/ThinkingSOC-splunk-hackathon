# Alert Service

Core alert processing pipeline. Receives Splunk webhook payloads, enriches them with inventory and graph data, classifies alerts into Security / Observability tracks, and orchestrates agent triage.

**Auto ingestion:** when `TSOC_INGEST_AUTO_ANALYZE=true` in `backend/.env` (default after `install.sh`), `ingest_background.run_post_ingest` runs triage after each webhook. This is **not** configurable via URL query parameters — see `backend/middleware/reject_config_query.py`.

## Key files

| File | Description |
|------|-------------|
| `alert_pipeline.py` | Fetches Splunk search results via REST and enriches alert payloads |
| `alert_classifier.py` | Rule-based hybrid classifier for Security vs Observability routing |
| `alert_classifier_llm.py` | Optional LiteLLM fallback when rule-based confidence is low |
| `alert_mcp_enrichment.py` | MCP metadata enrichment before classification |
| `alert_fields.py` | Flattens Splunk alert/result rows for LLM system context |
| `enrichment_resolver.py` | Resolves inventory rows and user–asset relationships for alerts |
| `graph_correlation.py` | Derives Neo4j correlation fields from Splunk webhook rows |
| `agent_triage.py` | Shared triage orchestration (API + background ingest) |
| `ingest_background.py` | Post-ingest background persistence and optional agent triage |

## Related docs

- [Agents and Pipelines](../../../docs/04-agents-and-pipelines.md)
- [Low-Level Design](../../../docs/07-lld-low-level-design.md)
