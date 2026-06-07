# post-configure-pc

## Overview

Community of 5 nodes

- **Size**: 5 nodes
- **Cohesion**: 0.1143
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _pc_litellm_model_default | Function | install/modules/post_configure/litellm.sh | 4-12 |
| _pc_litellm_api_base_default | Function | install/modules/post_configure/litellm.sh | 14-16 |
| _pc_normalize_prompt_choice | Function | install/modules/post_configure/litellm.sh | 18-25 |
| _pc_prompt_litellm_model | Function | install/modules/post_configure/litellm.sh | 27-69 |
| _pc_prompt_litellm_config | Function | install/modules/post_configure/litellm.sh | 72-98 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `echo` (13 edge(s))
- `_pc_env_get` (3 edge(s))
- `ok` (3 edge(s))
- `prompt_input` (3 edge(s))
- `warn` (2 edge(s))
- `prompt_secret` (1 edge(s))
- `info` (1 edge(s))

### Incoming

- `install/modules/post_configure/litellm.sh` (5 edge(s))
