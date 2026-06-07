# soc-rag-retrieve

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.0741
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| retrieve_rag_documents | Function | backend/services/soc_rag/retrieve.py | 18-114 |
| _hits_log_line | Function | backend/services/soc_rag/retrieve.py | 117-130 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `info` (6 edge(s))
- `len` (5 edge(s))
- `perf_counter` (3 edge(s))
- `append` (2 edge(s))
- `format` (2 edge(s))
- `join` (1 edge(s))
- `qdrant_enabled` (1 edge(s))
- `search_qdrant_documents` (1 edge(s))
- `warning` (1 edge(s))
- `search_rag_documents` (1 edge(s))

### Incoming

- `backend/services/soc_rag/retrieve.py` (2 edge(s))
