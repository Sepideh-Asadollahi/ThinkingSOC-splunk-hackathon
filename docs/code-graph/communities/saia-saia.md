# saia-saia

## Overview

Community of 3 nodes

- **Size**: 3 nodes
- **Cohesion**: 0.0952
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| truncate_saia_prompt | Function | backend/splunk/mcp/saia/prompt.py | 13-19 |
| build_saia_generate_args | Function | backend/splunk/mcp/saia/prompt.py | 22-93 |
| build_nl_query | Function | backend/splunk/mcp/saia/prompt.py | 96-117 |

## Execution Flows

- **build_nl_query** (criticality: 0.45, depth: 2)

## Dependencies

### Outgoing

- `format` (11 edge(s))
- `append` (8 edge(s))
- `strip` (5 edge(s))
- `len` (3 edge(s))
- `join` (2 edge(s))
- `get` (1 edge(s))
- `saia_mcp_prompt_max_chars` (1 edge(s))
- `dumps` (1 edge(s))
- `bool` (1 edge(s))
- `getattr` (1 edge(s))
- `saia_aux_context_max_chars` (1 edge(s))

### Incoming

- `backend/splunk/mcp/saia/prompt.py` (3 edge(s))
