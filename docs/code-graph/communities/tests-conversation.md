# tests-conversation

## Overview

Community of 4 nodes

- **Size**: 4 nodes
- **Cohesion**: 0.2667
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| build_conversation_context | Function | backend/services/soc_rag/chat_history.py | 102-143 |
| test_build_conversation_context_short_thread | Test | backend/tests/test_soc_chat_conversations.py | 36-45 |
| _Settings | Class | backend/tests/test_soc_chat_conversations.py | 49-52 |
| test_build_conversation_context_long_thread_uses_rag | Test | backend/tests/test_soc_chat_conversations.py | 48-63 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `max` (3 edge(s))
- `int` (3 edge(s))
- `dumps` (3 edge(s))
- `get` (3 edge(s))
- `len` (1 edge(s))
- `append` (1 edge(s))
- `sort` (1 edge(s))
- `range` (1 edge(s))

### Incoming

- `backend/tests/test_soc_chat_conversations.py` (4 edge(s))
- `backend/services/soc_rag/chat_history.py` (1 edge(s))
- `range` (1 edge(s))
