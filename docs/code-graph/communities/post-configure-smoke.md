# post-configure-smoke

## Overview

Community of 4 nodes

- **Size**: 4 nodes
- **Cohesion**: 0.4884
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| run_integration_configure_smoke | Function | install/modules/post_configure/smoke.sh | 4-194 |
| _pc_smoke_ok | Function | install/modules/post_configure/smoke.sh | 9-9 |
| _pc_smoke_fail | Function | install/modules/post_configure/smoke.sh | 10-10 |
| _pc_smoke_warn | Function | install/modules/post_configure/smoke.sh | 11-11 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `_pc_env_get` (13 edge(s))
- `echo` (7 edge(s))
- `err` (3 edge(s))
- `ok` (3 edge(s))
- `return` (3 edge(s))
- `warn` (2 edge(s))
- `info` (2 edge(s))
- `step` (1 edge(s))
- `_tsoc_curl_ok` (1 edge(s))
- `_tsoc_tcp_port_in_use` (1 edge(s))
- `_wait_for_backend_with_embedding_notice` (1 edge(s))
- `_pc_parse_mgmt_url` (1 edge(s))
- `_pc_test_splunk_rest_login` (1 edge(s))
- `_pc_test_mcp_status_api` (1 edge(s))

### Incoming

- `install/modules/post_configure/smoke.sh` (4 edge(s))
