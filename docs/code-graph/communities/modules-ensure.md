# modules-ensure

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.0879
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| ensure_apt_updated | Function | install/modules/prerequisites.sh | 141-147 |
| install_missing_prerequisites | Function | install/modules/prerequisites.sh | 149-304 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `apt_install_packages` (13 edge(s))
- `info` (11 edge(s))
- `ok` (10 edge(s))
- `err` (8 edge(s))
- `apt_update_lists` (4 edge(s))
- `exit` (4 edge(s))
- `run_cmd` (3 edge(s))
- `echo` (2 edge(s))
- `cat` (2 edge(s))
- `dpkg` (2 edge(s))
- `apt-cache` (2 edge(s))
- `"$PYTHON_CMD"` (2 edge(s))
- `$NEED_CORE_TOOLS` (1 edge(s))
- `$NEED_GIT` (1 edge(s))
- `$NEED_DOCKER` (1 edge(s))

### Incoming

- `install/modules/prerequisites.sh` (2 edge(s))
