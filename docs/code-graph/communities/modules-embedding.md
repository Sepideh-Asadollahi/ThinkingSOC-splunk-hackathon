# modules-embedding

## Overview

Community of 8 nodes

- **Size**: 8 nodes
- **Cohesion**: 0.0980
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _tsoc_curl_ok | Function | install/modules/embedding.sh | 5-7 |
| _hint_to_bytes | Function | install/modules/embedding.sh | 9-16 |
| _bytes_human | Function | install/modules/embedding.sh | 18-27 |
| _embedding_install_meta | Function | install/modules/embedding.sh | 29-49 |
| _print_embedding_download_intro | Function | install/modules/embedding.sh | 87-105 |
| _monitor_embedding_download_progress | Function | install/modules/embedding.sh | 107-155 |
| ensure_embedding_model_for_install | Function | install/modules/embedding.sh | 157-208 |
| _wait_for_backend_with_embedding_notice | Function | install/modules/embedding.sh | 211-259 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `echo` (19 edge(s))
- `printf` (12 edge(s))
- `return` (11 edge(s))
- `info` (6 edge(s))
- `awk` (5 edge(s))
- `tr` (4 edge(s))
- `err` (3 edge(s))
- `ok` (3 edge(s))
- `cd` (2 edge(s))
- `date` (2 edge(s))
- `du` (2 edge(s))
- `sleep` (2 edge(s))
- `read` (2 edge(s))
- `warn` (2 edge(s))
- `"$venv_python"` (1 edge(s))

### Incoming

- `install/modules/embedding.sh` (8 edge(s))
