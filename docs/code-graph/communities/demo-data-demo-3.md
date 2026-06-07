# demo-data-demo

## Overview

Community of 4 nodes

- **Size**: 4 nodes
- **Cohesion**: 0.1190
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _demo_backend_bearer_token | Function | install/modules/demo_data/api_check.sh | 38-46 |
| _demo_curl_backend_json | Function | install/modules/demo_data/api_check.sh | 48-61 |
| _demo_log_api_endpoint | Function | install/modules/demo_data/api_check.sh | 63-90 |
| _demo_log_api_visibility | Function | install/modules/demo_data/api_check.sh | 92-120 |

## Execution Flows

- **_demo_log_api_visibility** (criticality: 0.44, depth: 3)

## Dependencies

### Outgoing

- `echo` (4 edge(s))
- `true` (3 edge(s))
- `return` (3 edge(s))
- `curl` (3 edge(s))
- `_demo_log_warn` (3 edge(s))
- `grep` (2 edge(s))
- `head` (2 edge(s))
- `cut` (2 edge(s))
- `_demo_log_curl_body_preview` (2 edge(s))
- `_demo_log` (2 edge(s))
- `mktemp` (1 edge(s))
- `python3` (1 edge(s))
- `rm` (1 edge(s))
- `_demo_log_section` (1 edge(s))
- `_demo_log_token_status` (1 edge(s))

### Incoming

- `install/modules/demo_data/api_check.sh` (4 edge(s))
