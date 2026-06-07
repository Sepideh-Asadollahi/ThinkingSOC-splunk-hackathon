# post-configure-pc

## Overview

Community of 5 nodes

- **Size**: 5 nodes
- **Cohesion**: 0.0820
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _pc_tsoc_uses_systemd | Function | install/modules/post_configure/restart.sh | 4-8 |
| _pc_print_manual_tsoc_restart_instructions | Function | install/modules/post_configure/restart.sh | 10-32 |
| _pc_verify_tsoc_services_running | Function | install/modules/post_configure/restart.sh | 34-65 |
| _pc_restart_tsoc_services_for_env | Function | install/modules/post_configure/restart.sh | 68-99 |
| _pc_restart_backend_for_env | Function | install/modules/post_configure/restart.sh | 102-104 |

## Execution Flows

- **_pc_restart_backend_for_env** (criticality: 0.43, depth: 2)

## Dependencies

### Outgoing

- `echo` (16 edge(s))
- `warn` (9 edge(s))
- `return` (9 edge(s))
- `systemctl` (3 edge(s))
- `run_cmd` (2 edge(s))
- `true` (2 edge(s))
- `_tsoc_tcp_port_in_use` (2 edge(s))
- `_tsoc_curl_ok` (2 edge(s))
- `err` (1 edge(s))
- `info` (1 edge(s))
- `_wait_for_backend_with_embedding_notice` (1 edge(s))
- `_wait_for_http` (1 edge(s))
- `restart_application_services` (1 edge(s))
- `ok` (1 edge(s))

### Incoming

- `install/modules/post_configure/restart.sh` (5 edge(s))
