# tests-merge

## Overview

Community of 5 nodes

- **Size**: 5 nodes
- **Cohesion**: 0.3415
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| merge_request_messages | Function | backend/services/soc_rag/chat_store.py | 330-362 |
| SocChatMessage | Class | backend/services/soc_rag/models.py | 46-48 |
| test_merge_request_messages_appends_new_user | Test | backend/tests/test_soc_chat_conversations.py | 12-19 |
| test_merge_request_messages_uses_full_client_history | Test | backend/tests/test_soc_chat_conversations.py | 22-33 |
| test_resolve_empty_conversation_does_not_recreate | Test | backend/tests/test_soc_chat_conversations.py | 66-97 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `patch` (3 edge(s))
- `len` (2 edge(s))
- `lower` (1 edge(s))
- `strip` (1 edge(s))
- `enumerate` (1 edge(s))
- `BaseModel` (1 edge(s))
- `get_settings` (1 edge(s))
- `SocChatRequest` (1 edge(s))
- `_resolve_conversation_messages` (1 edge(s))
- `assert_awaited_once_with` (1 edge(s))
- `assert_not_awaited` (1 edge(s))

### Incoming

- `backend/tests/test_soc_chat_conversations.py` (3 edge(s))
- `patch` (3 edge(s))
- `backend/services/soc_rag/chat_store.py` (1 edge(s))
- `backend/services/soc_rag/models.py` (1 edge(s))
- `get_settings` (1 edge(s))
- `SocChatRequest` (1 edge(s))
- `_resolve_conversation_messages` (1 edge(s))
- `assert_awaited_once_with` (1 edge(s))
- `assert_not_awaited` (1 edge(s))
