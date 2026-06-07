# modules-tsoc

## Overview

Community of 4 nodes

- **Size**: 4 nodes
- **Cohesion**: 0.0476
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _tsoc_docker_stack_detected | Function | install/modules/docker_stack.sh | 38-55 |
| _tsoc_stop_app_services_for_docker_reset | Function | install/modules/docker_stack.sh | 57-65 |
| _reset_tsoc_docker_stack | Function | install/modules/docker_stack.sh | 67-100 |
| prompt_and_reset_tsoc_docker_stack | Function | install/modules/docker_stack.sh | 102-127 |

## Execution Flows

- **prompt_and_reset_tsoc_docker_stack** (criticality: 0.37, depth: 2)

## Dependencies

### Outgoing

- `echo` (11 edge(s))
- `docker` (9 edge(s))
- `return` (8 edge(s))
- `info` (6 edge(s))
- `true` (6 edge(s))
- `grep` (4 edge(s))
- `warn` (2 edge(s))
- `systemctl` (2 edge(s))
- `cd` (1 edge(s))
- `run_cmd` (1 edge(s))
- `read` (1 edge(s))
- `continue` (1 edge(s))
- `ok` (1 edge(s))
- `stop_application_services` (1 edge(s))
- `prompt_yn` (1 edge(s))

### Incoming

- `install/modules/docker_stack.sh` (4 edge(s))
