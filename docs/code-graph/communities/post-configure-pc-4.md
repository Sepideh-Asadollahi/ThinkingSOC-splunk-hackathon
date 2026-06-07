# post-configure-pc

## Overview

Community of 4 nodes

- **Size**: 4 nodes
- **Cohesion**: 0.1290
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _pc_env_key_is_secret | Function | install/modules/post_configure/summary.sh | 39-47 |
| _pc_format_env_display_value | Function | install/modules/post_configure/summary.sh | 49-64 |
| _pc_print_env_file_summary | Function | install/modules/post_configure/summary.sh | 66-80 |
| _pc_print_post_install_env_summary | Function | install/modules/post_configure/summary.sh | 82-105 |

## Execution Flows

- **_pc_print_post_install_env_summary** (criticality: 0.44, depth: 3)

## Dependencies

### Outgoing

- `echo` (14 edge(s))
- `return` (4 edge(s))
- `warn` (2 edge(s))
- `shift` (1 edge(s))
- `_pc_env_get` (1 edge(s))
- `step` (1 edge(s))

### Incoming

- `install/modules/post_configure/summary.sh` (4 edge(s))
