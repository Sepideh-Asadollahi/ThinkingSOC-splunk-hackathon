# soc-rag-chat

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.1000
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| chat_message_doc_id | Function | backend/services/soc_rag/chat_history.py | 20-21 |
| index_chat_message_for_rag | Function | backend/services/soc_rag/chat_history.py | 24-48 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `format` (2 edge(s))
- `strip` (1 edge(s))
- `RagAlertDocument` (1 edge(s))
- `str` (1 edge(s))
- `int` (1 edge(s))
- `upsert_rag_document` (1 edge(s))

### Incoming

- `backend/services/soc_rag/chat_history.py` (2 edge(s))
