# demo-data-demo

## Overview

Community of 6 nodes

- **Size**: 6 nodes
- **Cohesion**: 0.4074
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _demo_log | Function | install/modules/demo_data/logging.sh | 32-38 |
| _demo_log_warn | Function | install/modules/demo_data/logging.sh | 40-46 |
| _demo_log_section | Function | install/modules/demo_data/logging.sh | 56-63 |
| _demo_log_file_stat | Function | install/modules/demo_data/logging.sh | 65-76 |
| _demo_log_paths_and_sources | Function | install/modules/demo_data/logging.sh | 78-116 |
| _demo_log_restore_hint | Function | install/modules/demo_data/logging.sh | 118-124 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `echo` (6 edge(s))
- `date` (2 edge(s))
- `info` (2 edge(s))
- `cut` (2 edge(s))
- `grep` (2 edge(s))
- `docker` (2 edge(s))
- `du` (1 edge(s))
- `wc` (1 edge(s))
- `tr` (1 edge(s))
- `_demo_dump_file` (1 edge(s))
- `_demo_snapshot_manifest` (1 edge(s))
- `_demo_snapshot_dir` (1 edge(s))
- `head` (1 edge(s))
- `true` (1 edge(s))
- `_demo_log_token_status` (1 edge(s))

### Incoming

- `install/modules/demo_data/logging.sh` (6 edge(s))
