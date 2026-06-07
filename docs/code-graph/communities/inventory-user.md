# inventory-user

## Overview

Community of 66 nodes

- **Size**: 66 nodes
- **Cohesion**: 0.3071
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| UserRecord | Class | backend/models/inventory.py | 10-16 |
| AssetRecord | Class | backend/models/inventory.py | 31-40 |
| RelationshipRecord | Class | backend/models/inventory.py | 58-62 |
| _norm_str | Function | backend/services/alert/enrichment_resolver.py | 33-36 |
| _rows_matching_exact | Function | backend/services/alert/enrichment_resolver.py | 39-56 |
| _pick_asset_row | Function | backend/services/alert/enrichment_resolver.py | 59-69 |
| _pick_user_row | Function | backend/services/alert/enrichment_resolver.py | 72-75 |
| _match_assets | Function | backend/services/alert/enrichment_resolver.py | 78-95 |
| _match_users | Function | backend/services/alert/enrichment_resolver.py | 98-120 |
| _asset_criticality_rank | Function | backend/services/alert/enrichment_resolver.py | 123-127 |
| _user_risk_rank | Function | backend/services/alert/enrichment_resolver.py | 130-137 |
| _pick_relationship_for_user | Function | backend/services/alert/enrichment_resolver.py | 140-153 |
| _pick_relationship_for_asset | Function | backend/services/alert/enrichment_resolver.py | 156-169 |
| _apply_relationships | Function | backend/services/alert/enrichment_resolver.py | 172-209 |
| enrich_from_inventory | Function | backend/services/alert/enrichment_resolver.py | 212-256 |
| _first | Function | backend/services/alert/graph_correlation.py | 35-40 |
| _is_private_ip | Function | backend/services/alert/graph_correlation.py | 43-54 |
| derive_alert_row_id | Function | backend/services/alert/graph_correlation.py | 57-61 |
| normalize_row_data | Function | backend/services/alert/graph_correlation.py | 64-76 |
| build_entity_identifiers | Function | backend/services/alert/graph_correlation.py | 79-102 |
| _severity_risk | Function | backend/services/alert/graph_correlation.py | 105-110 |
| _time_to_iso | Function | backend/services/alert/graph_correlation.py | 113-125 |
| build_correlation_block | Function | backend/services/alert/graph_correlation.py | 128-150 |
| _load_inventory | Function | backend/services/alert/graph_correlation.py | 153-165 |
| ensure_graph_correlation_on_payload | Function | backend/services/alert/graph_correlation.py | 168-197 |
| is_unique_violation | Function | backend/services/inventory/_db.py | 12-14 |
| raise_if_delete_missing | Function | backend/services/inventory/_db.py | 17-19 |
| dynamic_update | Function | backend/services/inventory/_db.py | 22-38 |
| list_assets | Function | backend/services/inventory/assets.py | 18-24 |
| get_asset | Function | backend/services/inventory/assets.py | 27-36 |
| create_asset | Function | backend/services/inventory/assets.py | 39-63 |
| update_asset | Function | backend/services/inventory/assets.py | 66-74 |
| delete_asset | Function | backend/services/inventory/assets.py | 77-81 |
| user_to_dict | Function | backend/services/inventory/converters.py | 10-18 |
| asset_to_dict | Function | backend/services/inventory/converters.py | 21-32 |
| relationship_to_dict | Function | backend/services/inventory/converters.py | 35-41 |
| user_record_to_dict | Function | backend/services/inventory/converters.py | 44-45 |
| asset_record_to_dict | Function | backend/services/inventory/converters.py | 48-49 |
| relationship_record_to_dict | Function | backend/services/inventory/converters.py | 52-53 |
| InventoryNotFoundError | Class | backend/services/inventory/exceptions.py | 4-5 |
| InventoryConflictError | Class | backend/services/inventory/exceptions.py | 8-9 |
| load_inventory_from_postgres | Function | backend/services/inventory/loader.py | 24-34 |
| relationship_record_from_row | Function | backend/services/inventory/relationships.py | 18-25 |
| list_relationships | Function | backend/services/inventory/relationships.py | 28-34 |
| get_relationship | Function | backend/services/inventory/relationships.py | 37-46 |
| create_relationship | Function | backend/services/inventory/relationships.py | 49-70 |
| update_relationship | Function | backend/services/inventory/relationships.py | 73-87 |
| delete_relationship | Function | backend/services/inventory/relationships.py | 90-97 |
| list_users | Function | backend/services/inventory/users.py | 16-22 |
| get_user | Function | backend/services/inventory/users.py | 25-34 |

*... and 16 more members.*

## Execution Flows

- **run_analysis** (criticality: 0.76, depth: 6)
- **run_observability_analysis** (criticality: 0.71, depth: 5)
- **enrich_endpoint** (criticality: 0.70, depth: 4)
- **ensure_graph_correlation_on_payload** (criticality: 0.69, depth: 4)
- **create_relationship** (criticality: 0.60, depth: 3)
- **update_relationship** (criticality: 0.60, depth: 3)
- **create_asset** (criticality: 0.59, depth: 2)
- **update_asset** (criticality: 0.59, depth: 2)
- **create_user** (criticality: 0.59, depth: 2)
- **update_user** (criticality: 0.59, depth: 2)
- *... and 4 more flows.*

## Dependencies

### Outgoing

- `get` (36 edge(s))
- `format` (19 edge(s))
- `str` (14 edge(s))
- `backend/services/splunk_json_store/__init__.py::ensure_pool` (13 edge(s))
- `acquire` (13 edge(s))
- `append` (11 edge(s))
- `lower` (10 edge(s))
- `strip` (10 edge(s))
- `dict` (8 edge(s))
- `execute` (7 edge(s))
- `model_dump` (6 edge(s))
- `len` (5 edge(s))
- `startswith` (4 edge(s))
- `patch` (4 edge(s))
- `BaseModel` (3 edge(s))

### Incoming

- `backend/services/alert/enrichment_resolver.py` (12 edge(s))
- `backend/services/alert/graph_correlation.py` (10 edge(s))
- `backend/tests/test_enrichment_resolver.py` (9 edge(s))
- `backend/models/inventory.py` (6 edge(s))
- `backend/services/inventory/converters.py` (6 edge(s))
- `backend/services/inventory/relationships.py` (6 edge(s))
- `backend/services/inventory/assets.py` (5 edge(s))
- `backend/services/inventory/users.py` (5 edge(s))
- `patch` (4 edge(s))
- `backend/services/inventory/_db.py` (3 edge(s))
- `backend/services/inventory/exceptions.py` (2 edge(s))
- `lower` (2 edge(s))
- `backend/tests/test_graph_correlation.py` (2 edge(s))
- `backend/tests/test_inventory_api.py` (2 edge(s))
- `get` (2 edge(s))
