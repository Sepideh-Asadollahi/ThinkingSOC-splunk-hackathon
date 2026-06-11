# backend/services

Parent: [README.md](../README.md)

Domain logic: ingest, classification, inventory enrichment, Security/Observability pipelines, triage, investigation SPL, SOC RAG, threat intel, and PostgreSQL persistence.

## Packages

| Package | Role |
|---------|------|
| [`alert/`](./alert/) | Webhook ingest, LLM classifier, MCP enrichment, agent triage, graph correlation hooks |
| [`inventory/`](./inventory/) | Users, assets, relationships, CSV seed, enrichment resolver |
| [`soc_analysis/`](./soc_analysis/) | Security pipeline runner (Defender / Hunter / Judge assembly) |
| [`soc_analysis_graph/`](./soc_analysis_graph/) | LangGraph nodes and state for the Security pipeline |
| [`observability_analysis/`](./observability_analysis/) | Observability pipeline (Entity → Impact → Diagnoser → Responder → Ops Judge) |
| [`investigation/`](./investigation/) | Investigation SPL, SAIA `/predict`, MCP execute, analyst workflow |
| [`triage/`](./triage/) | Post-analysis priority scoring and analyst queue |
| [`soc_rag/`](./soc_rag/) | Qdrant + FastEmbed RAG, SOC chat, Text-to-SQL |
| [`threat_intel/`](./threat_intel/) | VirusTotal API v3 enrichment and compact TI payloads |
| [`splunk_integration/`](./splunk_integration/) | Splunk AI Assistant and MCP service helpers |
| [`splunk_json_store/`](./splunk_json_store/) | PostgreSQL JSONB persistence (`tsoc_records`) |
| [`llm/`](./llm/) | LiteLLM wrapper, context budget, thinking extraction |
| [`platform/`](./platform/) | Dashboard KPIs, integration settings, host metrics |
| [`demo/`](./demo/) | PostgreSQL moment snapshot restore |
| [`prompts/`](./prompts/) | LLM system prompts (classifier, Hunter, Judge, SPL refine, …) |

## Root modules

- `correlation_integration.py` — mounts Neo4j graph API at `/api/v1/graph/*`

## See also

- [README.md](../README.md)
- [05-codebase-map.md](../../docs/05-codebase-map.md)
- [04-agents-and-pipelines.md](../../docs/04-agents-and-pipelines.md)
