# Codebase map

How to navigate the repository using the **code graph**, directory layout, and known **execution flows**. The graph is machine-generated; this document explains how to use it and where critical logic lives.

| Artifact | Link |
|----------|------|
| **Interactive graph** | [code-graph/graph.html](code-graph/graph.html) |
| **Community wiki** | [code-graph/communities/index.md](code-graph/communities/index.md) |
| **Build stats** | [code-graph/graph-status.txt](code-graph/graph-status.txt) |

## Graph snapshot

| Metric | Value |
|--------|------:|
| Indexed files | 140 |
| Nodes | 677 |
| Edges | 4,952 |
| Communities | 22 |
| Languages | Python, SQL |

**Indexed paths:** `backend/`, `thinking_soc_splunk_app/`, tests. Excluded: `node_modules`, `.venv`, `frontend/`, `project-engineering/`, generated caches.

Regenerate after large refactors:

```bash
bash scripts/build-code-graph.sh
```

## How to use the interactive graph

1. Open [graph.html](code-graph/graph.html) in a browser (offline-capable).
2. Search for a symbol (e.g. `splunk_ingest`, `run_soc_analysis_langgraph`).
3. Follow **edges** — imports, calls, and data flow hints between files.
4. Open the matching **community page** for a prose summary of a cohesive region.

Communities are clusters of files that change together — useful when onboarding to a feature area.

## Module dependency overview

```mermaid
flowchart TD
  subgraph edge ["Entry Points"]
    Ingest["routes/ingest.py"]
    Analysis["routes/analysis.py"]
    Agents["routes/agents.py"]
    Inventory["routes/inventory.py"]
    MCP_R["routes/mcp.py"]
  end

  subgraph services ["Domain Services"]
    Pipeline["alert_pipeline.py"]
    Classifier["alert_classifier*.py"]
    Enrichment["enrichment_resolver.py"]
    SOCGraph["soc_analysis_graph/"]
    ObsAnalysis["observability_analysis/"]
    Triage["triage_priority.py"]
    AdminGap["admin_org_gap.py"]
    Store["splunk_json_store.py"]
    InvLoader["inventory_loader.py"]
  end

  subgraph integration ["Integration"]
    REST["splunk/client/"]
    MCP_C["splunk/mcp/"]
    LiteLLM["litellm_service.py"]
  end

  subgraph data ["Data"]
    PG[("PostgreSQL")]
    Models["models/*"]
  end

  Ingest --> Pipeline --> REST
  Ingest --> Store
  Analysis --> SOCGraph
  Analysis --> InvLoader
  Agents --> Classifier --> LiteLLM
  Agents --> SOCGraph
  Inventory --> InvLoader --> PG
  MCP_R --> MCP_C

  SOCGraph --> LiteLLM
  SOCGraph --> MCP_C
  SOCGraph --> AdminGap
  SOCGraph --> Triage
  ObsAnalysis --> LiteLLM
  ObsAnalysis --> Triage
  Enrichment --> PG
  Store --> PG
  Pipeline --> Enrichment

  SOCGraph -.-> Models
  Classifier -.-> Models
  Enrichment -.-> Models
```

## Directory → concern map

| Directory | Primary concern | Start reading |
|-----------|-----------------|---------------|
| `backend/api/routes/ingest.py` | Webhook ingest, env-driven auto triage | First for Splunk handoff |
| `backend/middleware/reject_config_query.py` | Block config overrides via URL query | Security edge |
| `backend/api/routes/analysis.py` | Classify, route, SOC run-by-sid | Router + pipelines |
| `backend/api/routes/agents.py` | Triage orchestration | End-to-end agent response |
| `backend/api/routes/inventory.py` | Users, assets, relationships CRUD + enrich | Inventory admin |
| `backend/api/routes/mcp.py` | MCP status and proxies | Splunk MCP integration |
| `backend/services/alert_pipeline.py` | REST enrich | After ingest normalize |
| `backend/services/alert/alert_classifier_llm.py` | Routing | LLM-only Security vs Observability (exclusive) |
| `backend/services/alert/alert_classifier.py` | Routing | `manual_review` fallback when LLM unavailable |
| `backend/services/enrichment_resolver.py` | Enrichment engine | Alert → user/asset via inventory |
| `backend/services/inventory_loader.py` | PostgreSQL load | Pipeline inventory source |
| `backend/services/soc_analysis_graph/` | SOC LangGraph | Defender/Hunter/Judge |
| `backend/services/observability_analysis/` | Ops pipeline | Diagnoser/Responder/Ops Judge |
| `backend/services/splunk_json_store.py` | PostgreSQL records | All persistence |
| `backend/splunk/client/` | REST job results | Splunk 10+ v2 API |
| `backend/splunk/mcp/` | MCP JSON-RPC | SAIA / metadata / Hunter-Judge evidence |
| `backend/models/` | Contracts | Handoff + analysis shapes |
| `backend/devtools/` | SDK + CLI | External automation |
| `backend/data/demo/` | Demo snapshot + CSV | PostgreSQL seed when tables empty (`install.sh` / `setup.py`) |

Per-folder **`README.md`** files list immediate children — run `python3 scripts/generate-folder-readmes.py` to refresh indexes.

## Major communities (structural areas)

| Community | Nodes | What it represents |
|-----------|------:|---------------------|
| [routes-endpoint](code-graph/communities/routes-endpoint.md) | 86 | FastAPI routes, ingest, triage, storage HTTP |
| [tests-mcp](code-graph/communities/tests-mcp.md) | 78 | MCP and integration tests |
| [services-load](code-graph/communities/services-load.md) | 64 | Core services: analysis, MCP, inventory loaders |
| [inventory-identity](code-graph/communities/inventory-identity.md) | 39 | Inventory tables, relationships, PG store |
| [devtools-classify](code-graph/communities/devtools-classify.md) | 38 | SDK models and CLI commands |
| [services-report](code-graph/communities/services-report.md) | 27 | Batch runners and reporting helpers |
| [client-client](code-graph/communities/client-client.md) | 10 | Splunk REST HTTP client |
| [soc-analysis-graph-*](code-graph/communities/soc-analysis-graph-soc.md) | 2–6 each | Individual LangGraph nodes |

Full index: [code-graph/communities/index.md](code-graph/communities/index.md).

## Critical execution flows

Flows are ranked by graph **criticality** (how central the path is to the system). Use these as reading order for code archaeology.

| Flow | Criticality | Path (conceptual) |
|------|-------------|-------------------|
| `splunk_ingest` | 0.75 | `ingest.splunk_ingest` → `normalize_splunk_ingest_payload` → `enrich_alert_from_splunk` → store |
| `agent_triage_endpoint` | 0.74 | `agents` route → `run_agent_triage` → classify + pipelines |
| `assistant_spl_suggest` | 0.73 | `assistant` route → MCP SAIA / LiteLLM SPL |
| `run_routed_analysis_endpoint` | 0.73 | `analysis.route` → classifier → pipeline runners |
| `admin_org_gap_suggest` | 0.80 | Org context GAP suggestion (admin) |

### Flow: `splunk_ingest` (detail)

```
middleware/reject_config_query.py  (reject config query params → 400)
routes/ingest.py::splunk_ingest
  → models/handoff.py::normalize_splunk_ingest_payload
  → services/alert_pipeline.py::enrich_alert_from_splunk
       → splunk/client (REST results)
  → when TSOC_INGEST_AUTO_ANALYZE=true: BackgroundTasks run_post_ingest
       → services/ingest_background.py → agent_triage.py
  → else: persist_splunk_ingest_summary only
```

### Flow: Security analysis (detail)

```
routes/analysis.py (run or route)
  → services/inventory_loader.py::load_inventory_tables
  → services/soc_analysis.py::run_analysis
       → services/soc_analysis_graph/graph.py::run_soc_analysis_langgraph
            → nodes: prepare → risk_engine → … → judge → root_cause_spl
       → services/admin_org_gap.py::attach_admin_org_gap
  → splunk_json_store (persist soc_analysis + admin_org_gap_suggest)
```

## Tests as structural documentation

| Path | Covers |
|------|--------|
| `backend/tests/test_ingest_background.py` | Env-driven auto triage + rejected config query params |
| `backend/tests/test_sid_row_format.py` | `format_row_sid` / `splunk_job_sid` / `raw_alert` storage sid |
| `backend/tests/test_agent_triage_all_rows.py` | Sequential per-row ingest triage |
| `backend/tests/test_ingest_row_shape.py` | Multi-row detection + `ingest_row_shape` console logs |
| `backend/tests/test_reject_config_query.py` | Config query middleware |
| `backend/tests/test_inventory_api.py` | Inventory REST |
| `backend/tests/test_*mcp*` | MCP client behavior |
| `backend/tests/fixtures/` | Sample payloads |

Running tests (fast by default): `cd backend && .venv/bin/pytest` (after `setup.py`).

- Unit/API tests do **not** run external startup (Splunk login, embeddings warmup, correlation startup).
- Opt-in real FastAPI lifespan tests: `pytest -m real_startup -v -s`
- Opt-in live Splunk tests: `TSOC_RUN_SPLUNK_LIVE=1 pytest -m splunk_live -v -s`

## Models worth memorizing

| Model | File | Used for |
|-------|------|----------|
| `SplunkAlertIngest` | `models/handoff.py` | Webhook normalization |
| `AlertClassificationResult` | `models/agentic_ops.py` | Router output |
| `EnrichmentResult` | `models/enrichment.py` | Inventory enrichment output |
| `SocAnalysisResult` | `models/analysis.py` | Security pipeline response |

OpenAPI at `/docs` when the API is running lists request/response JSON schemas.

## Splunk app (minimal)

| Path | Role |
|------|------|
| `backend/data/demo/postgres_snapshot/` | Moment demo JSON (full inventory + 4 records) |
| `backend/data/demo/*.csv` | CSV fallback seed when snapshot manifest absent |
| `default/indexes.conf` | Demo index definition |
| No `bin/customalertaction` | Webhook only |

## Related documents

- [00-overview.md](./00-overview.md) — documentation index  
- [04-agents-and-pipelines.md](./04-agents-and-pipelines.md) — pipeline behavior  
- [03-architecture.md](./03-architecture.md) — runtime layers  
- [architecture_diagram.md](../architecture_diagram.md) — integration diagram  
- [07-lld-low-level-design.md](./07-lld-low-level-design.md) — API reference tables  
- [17-observability-pipeline.md](./17-observability-pipeline.md) — Observability pipeline code map  
- [18-llm-service-layer.md](./18-llm-service-layer.md) — LLM service code map  
- [19-storage-persistence.md](./19-storage-persistence.md) — storage layer code map  
- [21-database-schema.md](./21-database-schema.md) — database schema
