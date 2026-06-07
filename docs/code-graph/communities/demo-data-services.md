# demo-data-services

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.0204
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _tsoc_services_running_for_install | Function | install/modules/demo_data/steps.sh | 49-56 |
| _step_apply_demo_and_restart_services | Function | install/modules/demo_data/steps.sh | 59-123 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `_demo_log` (9 edge(s))
- `return` (5 edge(s))
- `_demo_log_warn` (5 edge(s))
- `_demo_log_postgres_counts` (3 edge(s))
- `_demo_log_restore_hint` (3 edge(s))
- `_pc_restart_tsoc_services_for_env` (2 edge(s))
- `systemctl` (2 edge(s))
- `_demo_restore_log_init` (1 edge(s))
- `_demo_log_section` (1 edge(s))
- `sync_demo_snapshot_to_install_dir` (1 edge(s))
- `_demo_db_bundle_complete` (1 edge(s))
- `_apply_demo_snapshot_to_postgres` (1 edge(s))
- `_demo_log_err` (1 edge(s))
- `bash` (1 edge(s))
- `_demo_sync_ingest_token_to_frontend` (1 edge(s))

### Incoming

- `install/modules/demo_data/steps.sh` (2 edge(s))
