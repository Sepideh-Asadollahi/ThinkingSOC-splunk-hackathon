# demo-data-sync

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.0238
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _sync_demo_dump_to_install_dir | Function | install/modules/demo_data/sync.sh | 4-33 |
| sync_demo_snapshot_to_install_dir | Function | install/modules/demo_data/sync.sh | 37-63 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `return` (10 edge(s))
- `_demo_log` (5 edge(s))
- `echo` (4 edge(s))
- `cut` (2 edge(s))
- `readlink` (2 edge(s))
- `info` (2 edge(s))
- `mkdir` (2 edge(s))
- `cp` (2 edge(s))
- `ok` (2 edge(s))
- `_demo_dump_file` (1 edge(s))
- `dirname` (1 edge(s))
- `stat` (1 edge(s))
- `du` (1 edge(s))
- `_demo_log_warn` (1 edge(s))
- `true` (1 edge(s))

### Incoming

- `install/modules/demo_data/sync.sh` (2 edge(s))
