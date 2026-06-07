# seed-seed

## Overview

Community of 3 nodes

- **Size**: 3 nodes
- **Cohesion**: 0.0741
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| seed_postgres | Function | correlation/seed/seed.py | 16-23 |
| seed_neo4j | Function | correlation/seed/seed.py | 26-42 |
| main | Function | correlation/seed/seed.py | 45-53 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `print` (3 edge(s))
- `get_settings` (2 edge(s))
- `execute_sql_file` (2 edge(s))
- `str` (2 edge(s))
- `close_pool` (1 edge(s))
- `close_driver` (1 edge(s))
- `read_text` (1 edge(s))
- `strip` (1 edge(s))
- `split` (1 edge(s))
- `get_driver` (1 edge(s))
- `session` (1 edge(s))
- `begin_transaction` (1 edge(s))
- `run` (1 edge(s))
- `commit` (1 edge(s))
- `rollback` (1 edge(s))

### Incoming

- `correlation/seed/seed.py` (4 edge(s))
