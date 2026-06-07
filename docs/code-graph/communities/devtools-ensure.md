# devtools-ensure

## Overview

Community of 5 nodes

- **Size**: 5 nodes
- **Cohesion**: 0.1600
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _skip_ensure | Function | backend/devtools/dev_postgres.py | 15-16 |
| _configured_dsn | Function | backend/devtools/dev_postgres.py | 19-21 |
| postgres_reachable | Function | backend/devtools/dev_postgres.py | 24-38 |
| probe | Function | backend/devtools/dev_postgres.py | 30-36 |
| ensure_dev_postgres | Function | backend/devtools/dev_postgres.py | 41-64 |

## Execution Flows

- **ensure_dev_postgres** (criticality: 0.37, depth: 2)

## Dependencies

### Outgoing

- `write` (3 edge(s))
- `strip` (2 edge(s))
- `get` (2 edge(s))
- `str` (2 edge(s))
- `lower` (1 edge(s))
- `insert` (1 edge(s))
- `step_docker_postgres` (1 edge(s))
- `SystemExit` (1 edge(s))
- `run` (1 edge(s))
- `connect` (1 edge(s))
- `close` (1 edge(s))

### Incoming

- `backend/devtools/dev_postgres.py` (5 edge(s))
