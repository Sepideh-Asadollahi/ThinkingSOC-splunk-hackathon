# soc-rag-conversation

## Overview

Community of 77 nodes

- **Size**: 77 nodes
- **Cohesion**: 0.1894
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _iso | Function | backend/api/routes/soc_chat.py | 45-48 |
| _conversation_summary | Function | backend/api/routes/soc_chat.py | 51-58 |
| soc_chat_list_conversations | Function | backend/api/routes/soc_chat.py | 66-74 |
| soc_chat_create_conversation | Function | backend/api/routes/soc_chat.py | 82-89 |
| soc_chat_get_conversation | Function | backend/api/routes/soc_chat.py | 97-125 |
| soc_chat_delete_conversation | Function | backend/api/routes/soc_chat.py | 132-141 |
| soc_chat_status | Function | backend/api/routes/soc_chat.py | 145-178 |
| resolve_snapshot_dir | Function | backend/services/demo/postgres_snapshot.py | 154-156 |
| snapshot_available | Function | backend/services/demo/postgres_snapshot.py | 159-160 |
| _prepare_bind | Function | backend/services/demo/postgres_snapshot.py | 183-196 |
| ensure_snapshot_schema | Function | backend/services/demo/postgres_snapshot.py | 199-209 |
| _inventory_empty | Function | backend/services/demo/postgres_snapshot.py | 212-216 |
| _expected_rows_from_manifest | Function | backend/services/demo/postgres_snapshot.py | 219-226 |
| _demo_bundle_needs_load | Function | backend/services/demo/postgres_snapshot.py | 229-249 |
| _truncate_demo_snapshot_tables | Function | backend/services/demo/postgres_snapshot.py | 252-257 |
| _reset_serial_sequences | Function | backend/services/demo/postgres_snapshot.py | 362-377 |
| _connect_for_restore | Function | backend/services/demo/postgres_snapshot.py | 380-390 |
| apply_postgres_demo_bundle | Function | backend/services/demo/postgres_snapshot.py | 393-423 |
| restore_postgres_snapshot_if_empty | Function | backend/services/demo/postgres_snapshot.py | 426-428 |
| _restore_into_conn | Function | backend/services/demo/postgres_snapshot.py | 431-459 |
| _title_from_text | Function | backend/services/soc_rag/chat_store.py | 43-49 |
| ensure_chat_schema | Function | backend/services/soc_rag/chat_store.py | 52-62 |
| list_conversations | Function | backend/services/soc_rag/chat_store.py | 65-90 |
| create_conversation | Function | backend/services/soc_rag/chat_store.py | 93-126 |
| get_or_create_conversation | Function | backend/services/soc_rag/chat_store.py | 129-148 |
| get_conversation | Function | backend/services/soc_rag/chat_store.py | 151-201 |
| delete_conversation | Function | backend/services/soc_rag/chat_store.py | 204-228 |
| load_conversation_messages | Function | backend/services/soc_rag/chat_store.py | 231-241 |
| append_messages | Function | backend/services/soc_rag/chat_store.py | 244-327 |
| list_embedding_model_options | Function | backend/services/soc_rag/embeddings.py | 36-52 |
| resolve_embedding_model | Function | backend/services/soc_rag/embeddings.py | 55-61 |
| _download_hint | Function | backend/services/soc_rag/embeddings.py | 64-69 |
| effective_embedding_dim | Function | backend/services/soc_rag/embeddings.py | 72-74 |
| fastembed_cache_dir | Function | backend/services/soc_rag/embeddings.py | 77-84 |
| _model_cache_folder_name | Function | backend/services/soc_rag/embeddings.py | 87-97 |
| _cache_has_onnx | Function | backend/services/soc_rag/embeddings.py | 100-104 |
| clear_embedding_cache | Function | backend/services/soc_rag/embeddings.py | 107-117 |
| _embedder | Function | backend/services/soc_rag/embeddings.py | 121-126 |
| embedding_dim_for_model | Function | backend/services/soc_rag/embeddings.py | 129-132 |
| _warmup_sync | Function | backend/services/soc_rag/embeddings.py | 135-152 |
| ensure_embedding_model | Function | backend/services/soc_rag/embeddings.py | 155-158 |
| _embed_sync | Function | backend/services/soc_rag/embeddings.py | 161-164 |
| embed_text | Function | backend/services/soc_rag/embeddings.py | 167-171 |
| SocChatConversationSummary | Class | backend/services/soc_rag/models.py | 71-76 |
| SocChatStoredMessage | Class | backend/services/soc_rag/models.py | 79-84 |
| SocChatConversationDetail | Class | backend/services/soc_rag/models.py | 87-92 |
| ensure_rag_schema | Function | backend/services/soc_rag/pg_store.py | 40-50 |
| upsert_rag_document | Function | backend/services/soc_rag/pg_store.py | 53-90 |
| _tokenize_query | Function | backend/services/soc_rag/pg_store.py | 93-94 |
| _score_row | Function | backend/services/soc_rag/pg_store.py | 97-102 |

*... and 27 more members.*

## Execution Flows

- **soc_chat_status** (criticality: 0.68, depth: 3)
- **soc_chat_create_conversation** (criticality: 0.60, depth: 3)
- **soc_chat_get_conversation** (criticality: 0.60, depth: 3)
- **soc_chat_list_conversations** (criticality: 0.59, depth: 2)
- **execute_sql** (criticality: 0.56, depth: 1)
- **soc_chat_delete_conversation** (criticality: 0.53, depth: 3)
- **search_rag_documents** (criticality: 0.49, depth: 2)
- **restore_postgres_snapshot_if_empty** (criticality: 0.48, depth: 4)
- **get_or_create_conversation** (criticality: 0.46, depth: 3)
- **load_conversation_messages** (criticality: 0.46, depth: 3)
- *... and 6 more flows.*

## Dependencies

### Outgoing

- `get` (57 edge(s))
- `append` (29 edge(s))
- `strip` (26 edge(s))
- `int` (21 edge(s))
- `str` (19 edge(s))
- `execute` (17 edge(s))
- `info` (14 edge(s))
- `acquire` (13 edge(s))
- `format` (13 edge(s))
- `isinstance` (12 edge(s))
- `fetchval` (8 edge(s))
- `len` (8 edge(s))
- `lower` (8 edge(s))
- `HTTPException` (6 edge(s))
- `loads` (6 edge(s))

### Incoming

- `backend/services/soc_rag/qdrant_store.py` (15 edge(s))
- `backend/services/soc_rag/embeddings.py` (14 edge(s))
- `backend/services/demo/postgres_snapshot.py` (13 edge(s))
- `backend/services/soc_rag/chat_store.py` (9 edge(s))
- `backend/api/routes/soc_chat.py` (7 edge(s))
- `backend/services/soc_rag/pg_store.py` (6 edge(s))
- `backend/services/splunk_json_store/pg.py` (5 edge(s))
- `backend/services/soc_rag/models.py` (3 edge(s))
- `backend/tests/test_qdrant_rag.py` (3 edge(s))
- `backend/services/soc_rag/sql_chat/execute.py` (2 edge(s))
- `backend/config.py::Settings` (2 edge(s))
