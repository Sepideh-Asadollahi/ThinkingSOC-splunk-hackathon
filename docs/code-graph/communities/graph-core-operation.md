# graph-core-operation

## Overview

Community of 10 nodes

- **Size**: 10 nodes
- **Cohesion**: 0.5758
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _utc_now | Function | correlation/graph_core/operation_store.py | 11-12 |
| OperationStore | Class | correlation/graph_core/operation_store.py | 15-101 |
| __init__ | Function | correlation/graph_core/operation_store.py | 16-18 |
| create | Function | correlation/graph_core/operation_store.py | 20-46 |
| get | Function | correlation/graph_core/operation_store.py | 48-50 |
| append_log | Function | correlation/graph_core/operation_store.py | 52-68 |
| complete | Function | correlation/graph_core/operation_store.py | 70-88 |
| fail | Function | correlation/graph_core/operation_store.py | 90-101 |
| OperationLogEntry | Class | correlation/graph_schemas/analysis.py | 20-23 |
| OperationStatusResponse | Class | correlation/graph_schemas/analysis.py | 26-34 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `append` (3 edge(s))
- `BaseModel` (2 edge(s))
- `Lock` (1 edge(s))
- `str` (1 edge(s))
- `uuid4` (1 edge(s))
- `now` (1 edge(s))

### Incoming

- `correlation/graph_core/operation_store.py` (3 edge(s))
- `correlation/graph_schemas/analysis.py` (2 edge(s))
