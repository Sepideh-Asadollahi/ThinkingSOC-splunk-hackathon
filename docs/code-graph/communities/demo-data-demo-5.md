# demo-data-demo

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.0333
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _demo_query_postgres_counts | Function | install/modules/demo_data/postgres.sh | 4-19 |
| _demo_db_bundle_complete | Function | install/modules/demo_data/postgres.sh | 22-37 |

## Execution Flows

- **_demo_db_bundle_complete** (criticality: 0.48, depth: 1)

## Dependencies

### Outgoing

- `return` (8 edge(s))
- `echo` (5 edge(s))
- `sed` (5 edge(s))
- `tr` (5 edge(s))
- `docker` (2 edge(s))
- `grep` (1 edge(s))
- `true` (1 edge(s))

### Incoming

- `install/modules/demo_data/postgres.sh` (2 edge(s))
