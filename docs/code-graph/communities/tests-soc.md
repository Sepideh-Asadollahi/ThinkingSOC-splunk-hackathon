# tests-soc

## Overview

Community of 4 nodes

- **Size**: 4 nodes
- **Cohesion**: 0.1176
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| test_run_soc_sql_chat_mocked | Test | backend/tests/test_soc_chat_sql.py | 81-134 |
| _FakeRow | Class | backend/tests/test_soc_chat_sql.py | 91-96 |
| keys | Function | backend/tests/test_soc_chat_sql.py | 92-93 |
| __getitem__ | Function | backend/tests/test_soc_chat_sql.py | 95-96 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `AsyncMock` (5 edge(s))
- `patch` (5 edge(s))
- `MagicMock` (2 edge(s))
- `model_copy` (1 edge(s))
- `backend/services/soc_rag/sql_chat/__init__.py::run_soc_sql_chat` (1 edge(s))

### Incoming

- `AsyncMock` (5 edge(s))
- `patch` (5 edge(s))
- `backend/tests/test_soc_chat_sql.py` (2 edge(s))
- `MagicMock` (2 edge(s))
- `model_copy` (1 edge(s))
- `backend/services/soc_rag/sql_chat/__init__.py::run_soc_sql_chat` (1 edge(s))
