# middleware-config

## Overview

Community of 4 nodes

- **Size**: 4 nodes
- **Cohesion**: 0.1667
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| forbidden_config_query_keys | Function | backend/middleware/reject_config_query.py | 35-50 |
| RejectConfigQueryParamsMiddleware | Class | backend/middleware/reject_config_query.py | 53-73 |
| dispatch | Function | backend/middleware/reject_config_query.py | 54-73 |
| test_forbidden_config_query_keys_detects_legacy_and_env_style | Test | backend/tests/test_reject_config_query.py | 10-26 |

## Execution Flows

- **dispatch** (criticality: 0.61, depth: 1)

## Dependencies

### Outgoing

- `append` (3 edge(s))
- `strip` (2 edge(s))
- `BaseHTTPMiddleware` (1 edge(s))
- `warning` (1 edge(s))
- `join` (1 edge(s))
- `JSONResponse` (1 edge(s))
- `call_next` (1 edge(s))
- `keys` (1 edge(s))
- `lower` (1 edge(s))
- `any` (1 edge(s))
- `startswith` (1 edge(s))
- `match` (1 edge(s))
- `sorted` (1 edge(s))
- `set` (1 edge(s))

### Incoming

- `backend/middleware/reject_config_query.py` (2 edge(s))
- `backend/tests/test_reject_config_query.py` (1 edge(s))
