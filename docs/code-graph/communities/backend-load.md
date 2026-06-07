# backend-load

## Overview

Community of 3 nodes

- **Size**: 3 nodes
- **Cohesion**: 0.0800
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _load_dotenv | Function | backend/run.py | 29-36 |
| _fail_if_port_in_use | Function | backend/run.py | 39-55 |
| main | Function | backend/run.py | 84-106 |

## Execution Flows

- **main** (criticality: 0.36, depth: 1)

## Dependencies

### Outgoing

- `get` (3 edge(s))
- `str` (2 edge(s))
- `socket` (1 edge(s))
- `setsockopt` (1 edge(s))
- `bind` (1 edge(s))
- `write` (1 edge(s))
- `format` (1 edge(s))
- `SystemExit` (1 edge(s))
- `close` (1 edge(s))
- `is_file` (1 edge(s))
- `load_dotenv` (1 edge(s))
- `chdir` (1 edge(s))
- `insert` (1 edge(s))
- `int` (1 edge(s))
- `strip` (1 edge(s))

### Incoming

- `backend/run.py` (4 edge(s))
