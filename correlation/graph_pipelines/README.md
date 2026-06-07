# graph_pipelines

Analysis pipelines that drive Attack Discovery — from alert filtering and clustering through LLM-based (or heuristic) report generation and cluster merging.

## Key files

| File | Description |
|------|-------------|
| `attack_alert_filter.py` | Attack filtering, entity clustering, anchor enrichment, indicator split, merge guard, cluster scoring |
| `demo_smart_analysis.py` | End-to-end pipeline — Neo4j load, clusters, LLM reports, findings insert (`incident-{hash}`) |
| `llm_stub.py` | LLM reports + cluster merge; heuristic fallback; respects indicator split guard |
| `correlation_logging.py` | Structured INFO-level logging helpers for pipeline step tracing (`correlation.discovery` logger) |
| `prompt_attack_discovery_system.md` | System prompt for LLM attack-discovery report generation |
| `prompt_cluster_merge_system.md` | System prompt for LLM cluster merge/separate decisions |

## Related docs

- [Correlation Graph Service](../../docs/12-correlation-graph-service.md)
