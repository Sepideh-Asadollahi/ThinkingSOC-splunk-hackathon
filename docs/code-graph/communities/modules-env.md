# modules-env

## Overview

Community of 11 nodes

- **Size**: 11 nodes
- **Cohesion**: 0.3378
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| setup_backend_env | Function | install/modules/project.sh | 58-76 |
| _fastembed_cache_dir | Function | install/modules/project.sh | 78-80 |
| _ensure_backend_env_defaults | Function | install/modules/project.sh | 82-90 |
| _ensure_ingest_auto_analyze_env | Function | install/modules/project.sh | 92-103 |
| _apply_install_embedding_defaults | Function | install/modules/project.sh | 105-115 |
| setup_frontend | Function | install/modules/project.sh | 127-159 |
| _ensure_frontend_env_defaults | Function | install/modules/project.sh | 161-181 |
| _sync_frontend_ingest_token_from_backend | Function | install/modules/project.sh | 184-193 |
| _upsert_env_default | Function | install/modules/project.sh | 195-201 |
| _upsert_env_line | Function | install/modules/project.sh | 203-210 |
| _npm_install_deps | Function | install/modules/project.sh | 212-218 |

## Execution Flows

- **setup_frontend** (criticality: 0.41, depth: 2)

## Dependencies

### Outgoing

- `return` (8 edge(s))
- `grep` (6 edge(s))
- `ok` (5 edge(s))
- `echo` (3 edge(s))
- `mkdir` (2 edge(s))
- `head` (2 edge(s))
- `cut` (2 edge(s))
- `run_cmd` (1 edge(s))
- `npm` (1 edge(s))
- `true` (1 edge(s))
- `sed` (1 edge(s))
- `err` (1 edge(s))
- `cp` (1 edge(s))
- `cd` (1 edge(s))
- `openssl` (1 edge(s))

### Incoming

- `install/modules/project.sh` (11 edge(s))
