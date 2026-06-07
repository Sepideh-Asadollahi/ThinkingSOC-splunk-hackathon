# modules-nodesource

## Overview

Community of 11 nodes

- **Size**: 11 nodes
- **Cohesion**: 0.1034
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| detect_python_cmd | Function | install/modules/prerequisites.sh | 15-29 |
| python_can_create_venv | Function | install/modules/prerequisites.sh | 33-36 |
| ensure_python_venv_package | Function | install/modules/prerequisites.sh | 38-64 |
| ensure_ca_certificates | Function | install/modules/prerequisites.sh | 66-72 |
| check_all_prerequisites | Function | install/modules/prerequisites.sh | 74-185 |
| cleanup_stale_nodesource_apt | Function | install/modules/prerequisites.sh | 194-199 |
| install_nodesource_gpg_key | Function | install/modules/prerequisites.sh | 201-210 |
| write_nodesource_apt_source | Function | install/modules/prerequisites.sh | 212-222 |
| install_nodesource_via_setup_script | Function | install/modules/prerequisites.sh | 224-233 |
| ensure_apt_updated | Function | install/modules/prerequisites.sh | 238-244 |
| install_missing_prerequisites | Function | install/modules/prerequisites.sh | 246-383 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `ok` (21 edge(s))
- `apt_install_packages` (14 edge(s))
- `info` (13 edge(s))
- `return` (13 edge(s))
- `warn` (12 edge(s))
- `err` (10 edge(s))
- `command_exists` (8 edge(s))
- `echo` (7 edge(s))
- `"$PYTHON_CMD"` (6 edge(s))
- `docker` (5 edge(s))
- `true` (5 edge(s))
- `awk` (4 edge(s))
- `apt_update_lists` (4 edge(s))
- `run_cmd` (4 edge(s))
- `apt-cache` (3 edge(s))

### Incoming

- `install/modules/prerequisites.sh` (11 edge(s))
