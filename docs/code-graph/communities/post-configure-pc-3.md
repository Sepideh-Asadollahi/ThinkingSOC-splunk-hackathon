# post-configure-pc

## Overview

Community of 4 nodes

- **Size**: 4 nodes
- **Cohesion**: 0.1190
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _pc_splunk_rest_creds_available | Function | install/modules/post_configure/mcp.sh | 4-16 |
| _pc_setup_splunk_mcp | Function | install/modules/post_configure/mcp.sh | 18-59 |
| _pc_mint_mcp_token | Function | install/modules/post_configure/mcp.sh | 61-80 |
| _pc_ensure_mcp_token | Function | install/modules/post_configure/mcp.sh | 83-105 |

## Execution Flows

- **_pc_ensure_mcp_token** (criticality: 0.48, depth: 1)

## Dependencies

### Outgoing

- `return` (10 edge(s))
- `warn` (7 edge(s))
- `_pc_env_get` (4 edge(s))
- `info` (4 edge(s))
- `ok` (3 edge(s))
- `true` (1 edge(s))
- `"$venv_python"` (1 edge(s))
- `"${cmd[@]}"` (1 edge(s))
- `read` (1 edge(s))
- `err` (1 edge(s))

### Incoming

- `install/modules/post_configure/mcp.sh` (4 edge(s))
