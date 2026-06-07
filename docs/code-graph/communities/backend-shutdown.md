# backend-shutdown

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.2500
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| shutdown_event | Function | backend/main.py | 65-66 |
| close_store | Function | backend/services/splunk_json_store.py | 76-83 |

## Execution Flows

- **shutdown_event** (criticality: 0.28, depth: 1)

## Dependencies

### Outgoing

- `close` (1 edge(s))

### Incoming

- `backend/main.py` (1 edge(s))
- `backend/services/splunk_json_store.py` (1 edge(s))
