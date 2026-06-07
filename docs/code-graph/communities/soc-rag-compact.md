# soc-rag-compact

## Overview

Community of 8 nodes

- **Size**: 8 nodes
- **Cohesion**: 0.1463
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _row_dict | Function | backend/services/soc_rag/compact_inventory.py | 13-18 |
| compact_user_document | Function | backend/services/soc_rag/compact_inventory.py | 21-54 |
| compact_asset_document | Function | backend/services/soc_rag/compact_inventory.py | 57-93 |
| compact_relationship_document | Function | backend/services/soc_rag/compact_inventory.py | 96-124 |
| index_inventory_catalog | Function | backend/services/soc_rag/compact_inventory.py | 127-149 |
| test_compact_user_document | Test | backend/tests/test_soc_rag_inventory_compact.py | 10-20 |
| test_compact_asset_document | Test | backend/tests/test_soc_rag_inventory_compact.py | 23-26 |
| test_compact_relationship_document | Test | backend/tests/test_soc_rag_inventory_compact.py | 29-34 |

## Execution Flows

- **index_inventory_catalog** (criticality: 0.37, depth: 2)

## Dependencies

### Outgoing

- `get` (19 edge(s))
- `str` (16 edge(s))
- `format` (7 edge(s))
- `_build_chunk_text` (3 edge(s))
- `RagAlertDocument` (3 edge(s))
- `make_doc_id` (3 edge(s))
- `upsert_rag_document` (3 edge(s))
- `dict` (2 edge(s))
- `isinstance` (1 edge(s))
- `hasattr` (1 edge(s))
- `model_dump` (1 edge(s))
- `list_users` (1 edge(s))
- `list_assets` (1 edge(s))
- `list_relationships` (1 edge(s))

### Incoming

- `backend/services/soc_rag/compact_inventory.py` (5 edge(s))
- `backend/tests/test_soc_rag_inventory_compact.py` (3 edge(s))
