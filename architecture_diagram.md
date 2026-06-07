# Architecture diagram

High-level integration and data flow for the **ThinkingSOC Agentic Ops Router**.

```mermaid
flowchart LR
  subgraph splunk ["Splunk 10+"]
    Webhook["Alert Webhook"]
    REST["REST API :8089"]
    MCP["MCP Server\n(App 7931)"]
    SAIA["AI Assistant\n/predict"]
  end

  subgraph backend ["FastAPI Backend :9876"]
    Ingest["Ingest API\nPOST /alerts/splunk-ingest"]
    Enrich["Inventory Enrichment\nusers / assets / relationships"]
    Router{"Agentic Ops Router\nLLM classifier (exclusive)"}

    subgraph secPipeline ["Security Pipeline"]
      Defender["Defender"]
      Hunter["Hunter\n+ MCP hunt queries"]
      Judge["Judge\n+ MCP SAIA verify"]
      VT["VirusTotal IOC\nenrichment"]
      InvSPL["Investigation SPL\nSAIA /predict + MCP execute"]
    end

    subgraph obsPipeline ["Observability Pipeline"]
      Entity["Entity Resolution"]
      Impact["Impact Context"]
      Diagnoser["Diagnoser"]
      Responder["Responder"]
      OpsJudge["Ops Judge"]
    end

    Triage["Triage Priority\nscore + verdict + queue"]
    AdminOrg["Admin Org GAP"]
    SOCChat["SOC Chat\nRAG + Text-to-SQL"]
    Dashboard["Dashboard\nKPIs + health + timeline"]
    Timeline["Investigation Workflow\ntimeline + analyst actions"]
    LLM["LLM Service\nLiteLLM wrapper"]
  end

  subgraph stores ["Data Stores"]
    PG[("PostgreSQL\ntsoc_records\ninventory\nchat\nfindings")]
    Qdrant[("Qdrant\nvector embeddings\nSOC RAG")]
    Neo4j[("Neo4j\nalert graph\ncorrelation")]
  end

  subgraph frontend ["Next.js UI :3000"]
    AnalystUI["Analyst Dashboard\nTriage · Analysis\nCorrelation · Chat\nInventory"]
  end

  subgraph external ["External"]
    LLMProvider["LLM Provider\nOpenAI / Anthropic\nNVIDIA NIM / Qwen"]
    VTApi["VirusTotal API v3"]
  end

  Webhook -->|"sid + sample row"| Ingest
  Ingest -->|"GET /jobs/{sid}/results"| REST
  Ingest --> Enrich --> Router

  Router -->|security| Defender
  Router -->|observability| Entity
  Router -->|manual_review| Triage

  Defender --> Hunter --> Judge --> Triage
  VT --> Hunter
  Hunter -->|"MCP hunt"| MCP
  Judge -->|"MCP SAIA"| MCP
  InvSPL -->|"/predict"| SAIA
  InvSPL -->|"splunk_run_query"| MCP

  Entity --> Impact --> Diagnoser --> Responder --> OpsJudge --> Triage

  Triage --> AdminOrg
  Triage --> PG
  Triage --> Qdrant

  PG --> Dashboard
  PG --> SOCChat
  PG --> Timeline
  PG --> Neo4j
  Qdrant --> SOCChat

  LLM --> LLMProvider
  VT --> VTApi

  PG --> AnalystUI
  Qdrant --> AnalystUI
  Neo4j --> AnalystUI
```

## Data flow summary

| Step | Mechanism |
|------|-----------|
| **Alert handoff** | Splunk webhook → `POST /api/v1/alerts/splunk-ingest` (sid + sample row) |
| **Full job rows** | Splunk REST `GET /services/search/v2/jobs/{sid}/results` |
| **Inventory enrichment** | PostgreSQL `tsoc_users` / `tsoc_assets` / `tsoc_relationships` → identity + risk context |
| **Classification** | LLM-only router (full alert payload + optional MCP metadata) → **Security** or **Observability** (exclusive); `manual_review` when LLM unavailable |
| **Security pipeline** | LangGraph: Defender → Hunter → Judge (structured JSON) |
| **Observability pipeline** | Entity → Impact → Diagnoser → Responder → Ops Judge |
| **VirusTotal** | IOC extraction → VT API v3 lookups → compact threat intel for analysis |
| **MCP integration** | JSON-RPC at `/services/mcp` — `splunk_get_metadata`, `splunk_run_query`, `saia_*` tools |
| **Hunter / Judge evidence** | MCP live hunt queries + SAIA ask before LLM reasoning |
| **Investigation SPL** | SAIA REST `/predict` → LLM review → MCP execute (All Time) → refine loop |
| **Triage** | Priority scoring (critical/high/medium/low) + review verdict + analyst queue |
| **Correlation** | Neo4j alert graph — entity co-occurrence, campaign detection, Smart Attack Discovery |
| **SOC Chat** | RAG (Qdrant + FastEmbed) + Text-to-SQL (PostgreSQL) + session history |
| **Dashboard** | KPIs, 14-day activity timeline, triage charts, health score, system resources |
| **Investigation workflow** | Timeline reconstruction + analyst acknowledge / escalate (human-in-the-loop) |
| **Storage** | PostgreSQL `tsoc_records` JSONB — 11 record types for full audit trail |
| **LLM service** | LiteLLM wrapper — multi-provider, error classification, thinking extraction, context budget |

## Detailed documentation

| # | Document | Topic |
|---|----------|-------|
| 00–03 | [docs/](docs/README.md) | Overview, system, integration boundaries, architecture |
| 04 | [Agents & Pipelines](docs/04-agents-and-pipelines.md) | Router, Security/Observability pipelines |
| 06–07 | [HLD](docs/06-hld-high-level-design.md) / [LLD](docs/07-lld-low-level-design.md) | High/low level design |
| 08 | [Triage](docs/08-triage-priority-layer.md) | Priority scoring and queue |
| 09 | [VirusTotal](docs/09-virustotal-threat-intel.md) | IOC enrichment |
| 10 | [SOC RAG](docs/10-soc-vector-rag.md) | Chat, RAG, Text-to-SQL |
| 11 | [Environment](docs/11-environment-configuration.md) | All env variables |
| 12 | [Correlation](docs/12-correlation-graph-service.md) | Neo4j graph, findings, explorer |
| 13 | [Investigation SPL](docs/13-cim-investigation-spl-mcp.md) | SPL generation and execution |
| 14 | [Inventory](docs/14-inventory-service.md) | Users, assets, relationships |
| 15 | [Splunk MCP](docs/15-splunk-mcp-integration.md) | MCP client and SAIA tools |
| 16 | [Dashboard](docs/16-dashboard.md) | Analyst overview UI |
| 17 | [Observability](docs/17-observability-pipeline.md) | Observability pipeline detail |
| 18 | [LLM Service](docs/18-llm-service-layer.md) | LiteLLM, errors, thinking, budget |
| 19 | [Storage](docs/19-storage-persistence.md) | PostgreSQL persistence layer |
| 20 | [Investigation](docs/20-investigation-workflow.md) | Timeline and analyst actions |
| — | [Architecture Views](docs/architecture-views.md) | 8 multi-perspective Mermaid diagrams |
