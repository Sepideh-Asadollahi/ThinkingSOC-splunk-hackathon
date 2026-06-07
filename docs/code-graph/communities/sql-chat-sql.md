# sql-chat-sql

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.0400
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _strip_sql_comments | Function | backend/services/soc_rag/sql_chat/validator.py | 22-25 |
| validate_readonly_sql | Function | backend/services/soc_rag/sql_chat/validator.py | 28-63 |

## Execution Flows

- **validate_readonly_sql** (criticality: 0.61, depth: 1)

## Dependencies

### Outgoing

- `ValueError` (6 edge(s))
- `sub` (2 edge(s))
- `strip` (2 edge(s))
- `search` (2 edge(s))
- `format` (2 edge(s))
- `upper` (1 edge(s))
- `startswith` (1 edge(s))
- `finditer` (1 edge(s))
- `lower` (1 edge(s))
- `group` (1 edge(s))
- `append` (1 edge(s))
- `rstrip` (1 edge(s))
- `int` (1 edge(s))

### Incoming

- `backend/services/soc_rag/sql_chat/validator.py` (2 edge(s))
