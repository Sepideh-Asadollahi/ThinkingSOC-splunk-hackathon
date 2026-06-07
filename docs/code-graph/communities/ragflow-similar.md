# ragflow-similar

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.0278
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _truncate_similar_block | Function | backend/services/ragflow/similar.py | 19-31 |
| find_similar_alerts | Function | backend/services/ragflow/similar.py | 52-151 |

## Execution Flows

- **find_similar_alerts** (criticality: 0.36, depth: 1)

## Dependencies

### Outgoing

- `get` (5 edge(s))
- `str` (5 edge(s))
- `len` (3 edge(s))
- `append` (3 edge(s))
- `SimilarAlertContext` (2 edge(s))
- `SimilarAlertItem` (2 edge(s))
- `round` (2 edge(s))
- `dumps` (1 edge(s))
- `model_dump` (1 edge(s))
- `max` (1 edge(s))
- `compact_alert_document` (1 edge(s))
- `ragflow_enabled` (1 edge(s))
- `retrieve_chunks` (1 edge(s))
- `isinstance` (1 edge(s))
- `float` (1 edge(s))

### Incoming

- `backend/services/ragflow/similar.py` (2 edge(s))
