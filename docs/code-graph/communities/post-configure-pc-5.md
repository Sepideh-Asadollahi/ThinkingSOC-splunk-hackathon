# post-configure-pc

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.0909
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _pc_apply_frontend_env | Function | install/modules/post_configure/env_apply.sh | 32-43 |
| _pc_sync_ingest_token_to_frontend | Function | install/modules/post_configure/env_apply.sh | 46-58 |

## Execution Flows

- **_pc_apply_frontend_env** (criticality: 0.48, depth: 1)

## Dependencies

### Outgoing

- `_upsert_env_line` (3 edge(s))
- `return` (2 edge(s))
- `_pc_parse_mgmt_url` (1 edge(s))
- `ok` (1 edge(s))
- `_pc_env_get` (1 edge(s))

### Incoming

- `install/modules/post_configure/env_apply.sh` (2 edge(s))
