# demo-data-demo

## Overview

Community of 6 nodes

- **Size**: 6 nodes
- **Cohesion**: 0.0708
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _demo_env_token_len | Function | install/modules/demo_data/diagnostics.sh | 4-9 |
| _demo_log_token_status | Function | install/modules/demo_data/diagnostics.sh | 30-67 |
| _demo_log_services_status | Function | install/modules/demo_data/diagnostics.sh | 69-99 |
| _demo_log_bundle_complete_audit | Function | install/modules/demo_data/diagnostics.sh | 101-131 |
| _demo_log_record_type_breakdown | Function | install/modules/demo_data/diagnostics.sh | 133-150 |
| _demo_log_full_diagnostics | Function | install/modules/demo_data/diagnostics.sh | 232-240 |

## Execution Flows

- **_demo_log_full_diagnostics** (criticality: 0.45, depth: 2)

## Dependencies

### Outgoing

- `_demo_log` (21 edge(s))
- `echo` (14 edge(s))
- `_demo_log_warn` (9 edge(s))
- `true` (7 edge(s))
- `grep` (6 edge(s))
- `head` (5 edge(s))
- `_demo_log_section` (5 edge(s))
- `return` (5 edge(s))
- `sed` (5 edge(s))
- `tr` (5 edge(s))
- `cut` (4 edge(s))
- `docker` (4 edge(s))
- `systemctl` (2 edge(s))
- `_tsoc_tcp_port_in_use` (2 edge(s))
- `_demo_query_postgres_counts` (1 edge(s))

### Incoming

- `install/modules/demo_data/diagnostics.sh` (6 edge(s))
