# backend/tests

Parent: [README.md](../README.md)

Pytest unit and integration tests. Fast by default — no live Splunk, embedding warmup, or correlation startup unless opted in.

## Run

```bash
cd backend
source .venv/bin/activate   # or backend/.venv
pytest
```

### Markers

| Marker | When to use |
|--------|-------------|
| `real_startup` | Tests that need the full FastAPI lifespan (`pytest -m real_startup`) |
| `splunk_live` | Live Splunk MCP/SAIA (`TSOC_RUN_SPLUNK_LIVE=1` + valid Splunk creds) |

## Coverage areas

| Area | Example modules |
|------|-----------------|
| Ingest & webhook | `test_ingest*.py`, `test_buffered_job_enrich.py` |
| Classification & routing | `test_alert_classifier_llm.py`, `test_analysis.py` |
| Security / Observability pipelines | `test_analysis.py`, `test_observability.py` |
| Investigation SPL | `test_spl_predict_pipeline.py`, `test_investigation_*.py` |
| MCP & SAIA | `test_mcp_*.py`, `test_splunk_live_mcp_saia.py` |
| Inventory & enrichment | `test_inventory_*.py`, `test_enrichment_resolver.py` |
| Triage & dashboard | `test_triage_*.py`, `test_dashboard_*.py` |
| SOC RAG & chat | `test_qdrant_rag.py`, `test_soc_chat_*.py` |
| Threat intel | `test_virustotal*.py`, `test_threat_intel_compact.py` |
| Graph correlation | `test_graph_correlation.py` |
| SDK / devtools | `test_devtools_sdk.py` |

Fixtures: [`fixtures/`](./fixtures/)

## See also

- [README.md](../README.md)
- [05-codebase-map.md](../../docs/05-codebase-map.md)
