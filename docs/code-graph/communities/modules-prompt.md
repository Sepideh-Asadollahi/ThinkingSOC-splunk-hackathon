# modules-prompt

## Overview

Community of 7 nodes

- **Size**: 7 nodes
- **Cohesion**: 0.2800
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| warn | Function | install/modules/common.sh | 29-29 |
| err | Function | install/modules/common.sh | 30-30 |
| ask | Function | install/modules/common.sh | 32-32 |
| need_root | Function | install/modules/common.sh | 91-96 |
| prompt_yn | Function | install/modules/common.sh | 111-125 |
| prompt_input | Function | install/modules/common.sh | 127-137 |
| validate_repo_url | Function | install/modules/common.sh | 139-150 |

## Execution Flows

- **validate_repo_url** (criticality: 0.42, depth: 2)

## Dependencies

### Outgoing

- `echo` (5 edge(s))
- `exit` (2 edge(s))
- `return` (2 edge(s))
- `read` (2 edge(s))

### Incoming

- `install/modules/common.sh` (7 edge(s))
