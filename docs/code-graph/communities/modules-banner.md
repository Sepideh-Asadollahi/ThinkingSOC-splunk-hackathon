# modules-banner

## Overview

Community of 3 nodes

- **Size**: 3 nodes
- **Cohesion**: 0.1667
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _banner_visible_len | Function | install/modules/common.sh | 38-42 |
| center_line | Function | install/modules/common.sh | 44-53 |
| print_install_banner | Function | install/modules/common.sh | 55-79 |

## Execution Flows

- **print_install_banner** (criticality: 0.37, depth: 2)

## Dependencies

### Outgoing

- `echo` (8 edge(s))
- `printf` (3 edge(s))
- `tput` (2 edge(s))
- `sed` (1 edge(s))
- `wc` (1 edge(s))
- `tr` (1 edge(s))
- `(( pad < 0 ))` (1 edge(s))

### Incoming

- `install/modules/common.sh` (3 edge(s))
