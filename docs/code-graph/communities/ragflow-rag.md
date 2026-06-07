# ragflow-rag

## Overview

Community of 21 nodes

- **Size**: 21 nodes
- **Cohesion**: 0.1564
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| jsonb_param | Function | backend/services/splunk_json_store/pg.py | 15-19 |
| splunk_store_configured | Function | backend/services/splunk_json_store/pg.py | 39-41 |
| init_store | Function | backend/services/splunk_json_store/pg.py | 44-98 |
| ensure_pool | Function | backend/services/splunk_json_store/pg.py | 111-118 |
| submit_hec_event | Function | backend/services/splunk_json_store/pg.py | 121-151 |
| RagflowError | Class | backend/services/ragflow/client.py | 18-19 |
| ragflow_enabled | Function | backend/services/ragflow/client.py | 22-23 |
| _headers | Function | backend/services/ragflow/client.py | 26-31 |
| _base | Function | backend/services/ragflow/client.py | 34-35 |
| health_check | Function | backend/services/ragflow/client.py | 38-51 |
| _unwrap_data | Function | backend/services/ragflow/client.py | 54-57 |
| ensure_dataset | Function | backend/services/ragflow/client.py | 60-76 |
| upload_document_text | Function | backend/services/ragflow/client.py | 79-100 |
| retrieve_chunks | Function | backend/services/ragflow/client.py | 103-127 |
| ensure_rag_schema | Function | backend/services/ragflow/pg_store.py | 40-50 |
| upsert_rag_document | Function | backend/services/ragflow/pg_store.py | 53-84 |
| _tokenize_query | Function | backend/services/ragflow/pg_store.py | 102-103 |
| _score_row | Function | backend/services/ragflow/pg_store.py | 106-111 |
| search_rag_documents | Function | backend/services/ragflow/pg_store.py | 128-225 |
| rag_document_stats | Function | backend/services/ragflow/pg_store.py | 228-246 |
| soc_chat_status | Function | backend/api/routes/soc_chat.py | 25-37 |

## Execution Flows

- **soc_chat_status** (criticality: 0.60, depth: 3)
- **search_rag_documents** (criticality: 0.49, depth: 2)
- **upsert_rag_document** (criticality: 0.45, depth: 2)
- **upload_document_text** (criticality: 0.37, depth: 2)
- **retrieve_chunks** (criticality: 0.37, depth: 2)
- **ensure_pool** (criticality: 0.36, depth: 1)
- **submit_hec_event** (criticality: 0.36, depth: 1)

## Dependencies

### Outgoing

- `get` (25 edge(s))
- `append` (16 edge(s))
- `format` (14 edge(s))
- `isinstance` (12 edge(s))
- `strip` (10 edge(s))
- `str` (6 edge(s))
- `acquire` (6 edge(s))
- `execute` (6 edge(s))
- `int` (5 edge(s))
- `AsyncClient` (4 edge(s))
- `json` (4 edge(s))
- `post` (3 edge(s))
- `raise_for_status` (3 edge(s))
- `bool` (2 edge(s))
- `lower` (2 edge(s))

### Incoming

- `backend/services/ragflow/client.py` (9 edge(s))
- `backend/services/ragflow/pg_store.py` (6 edge(s))
- `backend/services/splunk_json_store/pg.py` (5 edge(s))
- `backend/api/routes/soc_chat.py` (1 edge(s))
