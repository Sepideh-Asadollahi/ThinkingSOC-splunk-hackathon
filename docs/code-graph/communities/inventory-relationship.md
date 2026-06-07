# inventory-relationship

## Overview

Community of 34 nodes

- **Size**: 34 nodes
- **Cohesion**: 0.2688
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| UserRecord | Class | backend/models/inventory.py | 10-16 |
| AssetRecord | Class | backend/models/inventory.py | 31-40 |
| RelationshipRecord | Class | backend/models/inventory.py | 58-62 |
| _load_inventory | Function | backend/services/alert/graph_correlation.py | 153-165 |
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
| create_user | Function | backend/services/inventory/users.py | 37-57 |
| update_user | Function | backend/services/inventory/users.py | 60-68 |
| delete_user | Function | backend/services/inventory/users.py | 71-75 |
| test_inventory_users_list_requires_pg_mock | Test | backend/tests/test_inventory_api.py | 26-34 |
| test_inventory_relationships_list | Test | backend/tests/test_inventory_api.py | 42-54 |

## Execution Flows

- **ensure_graph_correlation_on_payload** (criticality: 0.69, depth: 4)
- **create_relationship** (criticality: 0.60, depth: 3)
- **update_relationship** (criticality: 0.60, depth: 3)
- **create_asset** (criticality: 0.59, depth: 2)
- **update_asset** (criticality: 0.59, depth: 2)
- **create_user** (criticality: 0.59, depth: 2)
- **update_user** (criticality: 0.59, depth: 2)
- **delete_asset** (criticality: 0.48, depth: 2)
- **delete_relationship** (criticality: 0.48, depth: 2)
- **delete_user** (criticality: 0.48, depth: 2)
- *... and 1 more flows.*

## Dependencies

### Outgoing

- `format` (15 edge(s))
- `backend/services/splunk_json_store/__init__.py::ensure_pool` (13 edge(s))
- `acquire` (13 edge(s))
- `execute` (7 edge(s))
- `model_dump` (6 edge(s))
- `dict` (5 edge(s))
- `patch` (4 edge(s))
- `BaseModel` (3 edge(s))
- `str` (3 edge(s))
- `fetchrow` (3 edge(s))
- `fetch` (3 edge(s))
- `get` (3 edge(s))
- `json` (2 edge(s))
- `join` (1 edge(s))
- `enumerate` (1 edge(s))

### Incoming

- `backend/models/inventory.py` (6 edge(s))
- `backend/services/inventory/converters.py` (6 edge(s))
- `backend/services/inventory/relationships.py` (6 edge(s))
- `backend/services/inventory/assets.py` (5 edge(s))
- `backend/services/inventory/users.py` (5 edge(s))
- `patch` (4 edge(s))
- `backend/services/inventory/_db.py` (3 edge(s))
- `backend/services/inventory/exceptions.py` (2 edge(s))
- `backend/tests/test_inventory_api.py` (2 edge(s))
- `get` (2 edge(s))
- `json` (2 edge(s))
- `backend/services/alert/graph_correlation.py` (1 edge(s))
- `backend/services/alert/graph_correlation.py::ensure_graph_correlation_on_payload` (1 edge(s))
- `backend/services/inventory/loader.py` (1 edge(s))
