# thinking-soc-splunk-hackathon-setup

## Overview

Community of 23 nodes

- **Size**: 23 nodes
- **Cohesion**: 0.4402
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| info | Function | install.sh | 30-30 |
| ok | Function | install.sh | 31-31 |
| warn | Function | install.sh | 32-32 |
| err | Function | install.sh | 33-33 |
| step | Function | install.sh | 34-34 |
| ask | Function | install.sh | 35-35 |
| need_root | Function | install.sh | 38-43 |
| command_exists | Function | install.sh | 45-45 |
| detect_os | Function | install.sh | 47-56 |
| prompt_yn | Function | install.sh | 58-68 |
| check_all_prerequisites | Function | install.sh | 82-210 |
| ensure_apt_updated | Function | install.sh | 214-220 |
| install_missing_prerequisites | Function | install.sh | 222-356 |
| setup_repo | Function | install.sh | 359-372 |
| setup_venv | Function | install.sh | 375-400 |
| run_project_setup | Function | install.sh | 403-413 |
| setup_frontend | Function | install.sh | 416-452 |
| create_systemd_services | Function | install.sh | 455-511 |
| run_smoke_test | Test | install.sh | 514-626 |
| smoke_ok | Function | install.sh | 517-517 |
| smoke_fail | Function | install.sh | 518-518 |
| print_summary | Function | install.sh | 629-656 |
| main | Function | install.sh | 661-756 |

## Execution Flows

- **main** (criticality: 0.37, depth: 2)

## Dependencies

### Outgoing

- `echo` (53 edge(s))
- `apt-get` (19 edge(s))
- `docker` (9 edge(s))
- `"$PYTHON_CMD"` (7 edge(s))
- `systemctl` (7 edge(s))
- `awk` (5 edge(s))
- `curl` (5 edge(s))
- `git` (4 edge(s))
- `cat` (4 edge(s))
- `exit` (3 edge(s))
- `tr` (2 edge(s))
- `node` (2 edge(s))
- `$NEED_CORE_TOOLS` (2 edge(s))
- `$NEED_GIT` (2 edge(s))
- `$NEED_DOCKER` (2 edge(s))

### Incoming

- `install.sh` (24 edge(s))
