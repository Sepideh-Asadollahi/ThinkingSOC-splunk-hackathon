# modules-apt

## Overview

Community of 8 nodes

- **Size**: 8 nodes
- **Cohesion**: 0.3077
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| info | Function | install/modules/common.sh | 27-27 |
| init_install_verbose | Function | install/modules/common.sh | 34-40 |
| run_cmd | Function | install/modules/common.sh | 42-47 |
| curl_fetch | Function | install/modules/common.sh | 49-56 |
| apt_update_lists | Function | install/modules/common.sh | 58-64 |
| apt_upgrade_all | Function | install/modules/common.sh | 66-72 |
| apt_install_packages | Function | install/modules/common.sh | 74-80 |
| apt_remove_packages | Function | install/modules/common.sh | 82-89 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `apt-get` (5 edge(s))
- `true` (2 edge(s))
- `curl` (1 edge(s))
- `echo` (1 edge(s))
- `"$@"` (1 edge(s))

### Incoming

- `install/modules/common.sh` (8 edge(s))
