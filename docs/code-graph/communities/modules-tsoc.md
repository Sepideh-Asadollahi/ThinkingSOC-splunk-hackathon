# modules-tsoc

## Overview

Community of 11 nodes

- **Size**: 11 nodes
- **Cohesion**: 0.0985
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _tsoc_compose_executable | Function | install/modules/docker_stack.sh | 37-48 |
| _tsoc_enumerate_stack_volumes | Function | install/modules/docker_stack.sh | 50-61 |
| _tsoc_compose_in_backend | Function | install/modules/docker_stack.sh | 63-70 |
| _tsoc_docker_stack_detected | Function | install/modules/docker_stack.sh | 72-83 |
| _tsoc_stop_app_services_for_docker_reset | Function | install/modules/docker_stack.sh | 85-93 |
| _reset_tsoc_docker_stack | Function | install/modules/docker_stack.sh | 95-128 |
| prompt_and_reset_tsoc_docker_stack | Function | install/modules/docker_stack.sh | 130-156 |
| _wait_tsoc_stack_ready | Function | install/modules/docker_stack.sh | 158-185 |
| start_tsoc_docker_stack | Function | install/modules/docker_stack.sh | 187-220 |
| docker_pull_image_retry | Function | install/modules/docker_stack.sh | 222-246 |
| ensure_docker_stack_images | Function | install/modules/docker_stack.sh | 248-262 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `return` (25 edge(s))
- `echo` (14 edge(s))
- `docker` (12 edge(s))
- `info` (9 edge(s))
- `ok` (8 edge(s))
- `err` (7 edge(s))
- `true` (6 edge(s))
- `grep` (5 edge(s))
- `warn` (4 edge(s))
- `continue` (3 edge(s))
- `sleep` (3 edge(s))
- `read` (2 edge(s))
- `systemctl` (2 edge(s))
- `sort` (1 edge(s))
- `command_exists` (1 edge(s))

### Incoming

- `install/modules/docker_stack.sh` (11 edge(s))
