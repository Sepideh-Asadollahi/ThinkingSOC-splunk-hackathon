# modules-smoke

## Overview

Community of 3 nodes

- **Size**: 3 nodes
- **Cohesion**: 0.4634
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| run_smoke_test | Test | install/modules/smoke_and_summary.sh | 3-129 |
| smoke_ok | Function | install/modules/smoke_and_summary.sh | 6-6 |
| smoke_fail | Function | install/modules/smoke_and_summary.sh | 7-7 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `docker` (9 edge(s))
- `echo` (9 edge(s))
- `curl` (4 edge(s))
- `_backend_startup_diagnose` (3 edge(s))
- `systemctl` (2 edge(s))
- `_tsoc_tcp_port_in_use` (2 edge(s))
- `info` (2 edge(s))
- `_wait_for_backend_with_embedding_notice` (2 edge(s))
- `ok` (2 edge(s))
- `return` (2 edge(s))
- `"$INSTALL_DIR/backend/.venv/bin/python"` (1 edge(s))
- `grep` (1 edge(s))
- `warn` (1 edge(s))
- `err` (1 edge(s))

### Incoming

- `install/modules/smoke_and_summary.sh` (3 edge(s))
