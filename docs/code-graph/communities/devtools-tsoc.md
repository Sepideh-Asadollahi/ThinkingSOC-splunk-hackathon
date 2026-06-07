# devtools-tsoc

## Overview

Community of 11 nodes

- **Size**: 11 nodes
- **Cohesion**: 0.3269
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| TsocSdkClient | Class | backend/devtools/client.py | 27-121 |
| __init__ | Function | backend/devtools/client.py | 28-41 |
| _headers | Function | backend/devtools/client.py | 43-46 |
| _to_payload | Function | backend/devtools/client.py | 49-52 |
| _raise_api_error | Function | backend/devtools/client.py | 54-62 |
| _post_model | Function | backend/devtools/client.py | 64-89 |
| classify_alert | Function | backend/devtools/client.py | 91-95 |
| route_analysis | Function | backend/devtools/client.py | 97-101 |
| run_agent_triage | Function | backend/devtools/client.py | 103-107 |
| suggest_spl | Function | backend/devtools/client.py | 109-113 |
| mcp_status | Function | backend/devtools/client.py | 115-121 |

## Execution Flows

- **classify_alert** (criticality: 0.37, depth: 2)
- **route_analysis** (criticality: 0.37, depth: 2)
- **run_agent_triage** (criticality: 0.37, depth: 2)
- **suggest_spl** (criticality: 0.37, depth: 2)

## Dependencies

### Outgoing

- `format` (4 edge(s))
- `get` (2 edge(s))
- `max` (2 edge(s))
- `Client` (2 edge(s))
- `raise_for_status` (2 edge(s))
- `json` (2 edge(s))
- `TsocTimeoutError` (2 edge(s))
- `TsocApiError` (2 edge(s))
- `rstrip` (1 edge(s))
- `int` (1 edge(s))
- `float` (1 edge(s))
- `range` (1 edge(s))
- `post` (1 edge(s))
- `model_validate` (1 edge(s))
- `sleep` (1 edge(s))

### Incoming

- `backend/devtools/client.py` (1 edge(s))
