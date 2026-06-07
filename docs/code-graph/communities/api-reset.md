# api-reset

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.2500
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| reset_rate_limit_buckets | Function | backend/api/deps.py | 81-83 |
| clear_settings_cache | Function | backend/tests/conftest.py | 25-31 |

## Execution Flows

- **clear_settings_cache** (criticality: 0.40, depth: 1)

## Dependencies

### Outgoing

- `clear` (2 edge(s))
- `cache_clear` (2 edge(s))

### Incoming

- `backend/api/deps.py` (1 edge(s))
- `backend/tests/conftest.py` (1 edge(s))
