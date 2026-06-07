# soc-rag-correlation

## Overview

Community of 3 nodes

- **Size**: 3 nodes
- **Cohesion**: 0.0377
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _ensure_correlation_path | Function | backend/services/soc_rag/index_correlation.py | 44-47 |
| index_correlation_catalog | Function | backend/services/soc_rag/index_correlation.py | 50-141 |
| _index_neo4j_alerts | Function | backend/services/soc_rag/index_correlation.py | 144-212 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `warning` (9 edge(s))
- `get` (8 edge(s))
- `str` (5 edge(s))
- `strip` (4 edge(s))
- `isinstance` (3 edge(s))
- `upsert_rag_document` (3 edge(s))
- `run_read_query` (2 edge(s))
- `max` (2 edge(s))
- `info` (2 edge(s))
- `insert` (1 edge(s))
- `compact_graph_alert_document` (1 edge(s))
- `list` (1 edge(s))
- `compact_attack_path_document` (1 edge(s))
- `init_pool` (1 edge(s))
- `ensure_graph_schema` (1 edge(s))

### Incoming

- `backend/services/soc_rag/index_correlation.py` (3 edge(s))
