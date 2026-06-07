# tests-response

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.1818
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _ok_response | Function | backend/tests/test_devtools_sdk.py | 10-15 |
| test_sdk_classify_typed_response | Test | backend/tests/test_devtools_sdk.py | 18-33 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `MagicMock` (1 edge(s))
- `backend/devtools/__init__.py::TsocSdkClient` (1 edge(s))
- `patch` (1 edge(s))
- `classify_alert` (1 edge(s))

### Incoming

- `backend/tests/test_devtools_sdk.py` (2 edge(s))
- `backend/devtools/__init__.py::TsocSdkClient` (1 edge(s))
- `patch` (1 edge(s))
- `classify_alert` (1 edge(s))
