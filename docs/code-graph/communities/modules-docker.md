# modules-docker

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.0526
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| docker_pull_image_retry | Function | install/modules/docker_stack.sh | 10-34 |
| ensure_docker_stack_images | Function | install/modules/docker_stack.sh | 36-50 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `return` (5 edge(s))
- `docker` (3 edge(s))
- `ok` (3 edge(s))
- `err` (2 edge(s))
- `warn` (1 edge(s))
- `sleep` (1 edge(s))
- `info` (1 edge(s))

### Incoming

- `install/modules/docker_stack.sh` (2 edge(s))
