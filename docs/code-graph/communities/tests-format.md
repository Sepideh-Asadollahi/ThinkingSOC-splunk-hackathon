# tests-format

## Overview

Community of 3 nodes

- **Size**: 3 nodes
- **Cohesion**: 0.3077
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| format_conversation_for_sql | Function | backend/services/soc_rag/sql_chat/prompt_context.py | 9-30 |
| test_format_conversation_for_sql_latest_question | Test | backend/tests/test_soc_chat_sql.py | 262-268 |
| test_format_conversation_includes_history | Test | backend/tests/test_sql_prompt_context.py | 14-23 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `append` (2 edge(s))
- `strip` (1 edge(s))
- `len` (1 edge(s))
- `dumps` (1 edge(s))
- `join` (1 edge(s))

### Incoming

- `backend/services/soc_rag/sql_chat/prompt_context.py` (1 edge(s))
- `backend/tests/test_soc_chat_sql.py` (1 edge(s))
- `backend/tests/test_sql_prompt_context.py` (1 edge(s))
