# tests-parse

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.0909
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| test_parse_oneshot_json_fatal_message | Test | backend/tests/test_splunk_client.py | 91-93 |
| parse_oneshot_json | Function | backend/splunk/client/oneshot_json.py | 8-27 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `isinstance` (7 edge(s))
- `get` (4 edge(s))
- `str` (2 edge(s))
- `upper` (1 edge(s))
- `RuntimeError` (1 edge(s))
- `format` (1 edge(s))
- `raises` (1 edge(s))

### Incoming

- `backend/splunk/client/oneshot_json.py` (1 edge(s))
- `backend/tests/test_splunk_client.py` (1 edge(s))
- `raises` (1 edge(s))
