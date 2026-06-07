# modules-services

## Overview

Community of 9 nodes

- **Size**: 9 nodes
- **Cohesion**: 0.0968
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _tsoc_tcp_port_in_use | Function | install/modules/services.sh | 41-52 |
| ensure_frontend_production_build | Function | install/modules/services.sh | 54-74 |
| _tsoc_curl_ok | Function | install/modules/services.sh | 77-79 |
| _wait_for_http | Function | install/modules/services.sh | 81-96 |
| _backend_startup_diagnose | Function | install/modules/services.sh | 98-108 |
| start_application_services | Function | install/modules/services.sh | 110-149 |
| restart_application_services | Function | install/modules/services.sh | 151-156 |
| stop_application_services | Function | install/modules/services.sh | 158-173 |
| create_systemd_services | Function | install/modules/services.sh | 175-233 |

## Execution Flows

- **create_systemd_services** (criticality: 0.43, depth: 2)
- **restart_application_services** (criticality: 0.42, depth: 3)

## Dependencies

### Outgoing

- `info` (12 edge(s))
- `return` (11 edge(s))
- `ok` (8 edge(s))
- `run_cmd` (6 edge(s))
- `true` (5 edge(s))
- `err` (3 edge(s))
- `command` (3 edge(s))
- `cat` (3 edge(s))
- `cd` (3 edge(s))
- `warn` (2 edge(s))
- `grep` (2 edge(s))
- `sleep` (2 edge(s))
- `_wait_for_backend_with_embedding_notice` (2 edge(s))
- `nohup` (2 edge(s))
- `echo` (2 edge(s))

### Incoming

- `install/modules/services.sh` (9 edge(s))
