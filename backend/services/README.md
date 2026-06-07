<!-- folder-readme: auto -->
# backend/services

Parent: [README.md](../README.md)

Domain logic: ingest enrichment, inventory enrichment, pipelines, storage.

## Contents

- [`inventory/`](./inventory/)
- [`observability_analysis/`](./observability_analysis/)
- [`prompts/`](./prompts/)
- [`soc_analysis/`](./soc_analysis/)
- [`soc_analysis_graph/`](./soc_analysis_graph/)
- `__init__.py`
- `admin_org_gap.py`
- `agent_triage.py`
- `alert_classifier.py`
- `alert_classifier_llm.py`
- `alert_mcp_enrichment.py`
- `alert_pipeline.py`
- `enrichment_resolver.py`
- `inventory_loader.py`
- `ingest_background.py`
- `inventory_store.py`
- `litellm_service.py`
- `observability_analysis_batch.py`
- `observability_prompts.py`
- `soc_analysis_batch.py`
- `soc_analysis_canonical.py`
- `soc_analysis_json.py`
- `soc_analysis_prompts.py`
- `soc_analysis_risk.py`
- `soc_analysis_root_cause_spl.py`
- `soc_verdict.py`
- `spl_mcp_review.py`
- `splunk_ai_assistant.py`
- `splunk_json_store.py`
- `splunk_mcp_service.py`
- `virustotal.py` — IOC extraction and VT API v3 client
- `virustotal_schema.py` — official VT response envelope / summary parsing
- `threat_intel_compact.py` — compact `findings` for LLM and API

**Docs:** [09-virustotal-threat-intel.md](../../docs/09-virustotal-threat-intel.md)

## See also

- [README.md](../README.md)
- [05-codebase-map.md](../../docs/05-codebase-map.md)
