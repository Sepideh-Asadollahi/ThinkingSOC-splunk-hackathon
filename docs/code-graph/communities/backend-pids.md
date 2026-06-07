# backend-pids

## Overview

Community of 5 nodes

- **Size**: 5 nodes
- **Cohesion**: 0.0690
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _load_dotenv | Function | backend/run.py | 37-44 |
| _find_pids_on_port | Function | backend/run.py | 47-64 |
| _kill_pids | Function | backend/run.py | 67-90 |
| _free_port | Function | backend/run.py | 93-119 |
| main | Function | backend/run.py | 148-182 |

## Execution Flows

- **main** (criticality: 0.37, depth: 2)

## Dependencies

### Outgoing

- `format` (4 edge(s))
- `get` (4 edge(s))
- `write` (3 edge(s))
- `kill` (3 edge(s))
- `run` (2 edge(s))
- `int` (2 edge(s))
- `strip` (2 edge(s))
- `sleep` (2 edge(s))
- `str` (2 edge(s))
- `set` (1 edge(s))
- `splitlines` (1 edge(s))
- `finditer` (1 edge(s))
- `add` (1 edge(s))
- `group` (1 edge(s))
- `sorted` (1 edge(s))

### Incoming

- `backend/run.py` (6 edge(s))
