# soc-rag-similar

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.0417
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _truncate_similar_block | Function | backend/services/soc_rag/similar.py | 19-31 |
| find_similar_alerts | Function | backend/services/soc_rag/similar.py | 52-116 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `len` (3 edge(s))
- `str` (3 edge(s))
- `append` (2 edge(s))
- `SimilarAlertContext` (2 edge(s))
- `get` (2 edge(s))
- `dumps` (1 edge(s))
- `model_dump` (1 edge(s))
- `max` (1 edge(s))
- `backend/services/splunk_json_store/__init__.py::splunk_store_configured` (1 edge(s))
- `compact_alert_document` (1 edge(s))
- `retrieve_rag_documents` (1 edge(s))
- `SimilarAlertItem` (1 edge(s))
- `items` (1 edge(s))
- `round` (1 edge(s))

### Incoming

- `backend/services/soc_rag/similar.py` (2 edge(s))
