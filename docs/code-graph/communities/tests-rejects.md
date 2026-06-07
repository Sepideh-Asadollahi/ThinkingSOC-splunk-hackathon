# tests-rejects

## Overview

Community of 7 nodes

- **Size**: 7 nodes
- **Cohesion**: 0.1935
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| TestValidateReadonlySql | Class | backend/tests/test_soc_chat_sql.py | 21-51 |
| test_accepts_simple_count | Test | backend/tests/test_soc_chat_sql.py | 22-26 |
| test_rejects_delete | Test | backend/tests/test_soc_chat_sql.py | 28-30 |
| test_rejects_update_keyword | Test | backend/tests/test_soc_chat_sql.py | 32-37 |
| test_rejects_multiple_statements | Test | backend/tests/test_soc_chat_sql.py | 39-41 |
| test_rejects_unknown_table | Test | backend/tests/test_soc_chat_sql.py | 43-45 |
| test_accepts_graph_findings | Test | backend/tests/test_soc_chat_sql.py | 47-51 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `backend/services/soc_rag/sql_chat/__init__.py::validate_readonly_sql` (6 edge(s))
- `raises` (4 edge(s))
- `lower` (1 edge(s))
- `upper` (1 edge(s))

### Incoming

- `backend/services/soc_rag/sql_chat/__init__.py::validate_readonly_sql` (6 edge(s))
- `raises` (4 edge(s))
- `backend/tests/test_soc_chat_sql.py` (1 edge(s))
- `lower` (1 edge(s))
- `upper` (1 edge(s))
