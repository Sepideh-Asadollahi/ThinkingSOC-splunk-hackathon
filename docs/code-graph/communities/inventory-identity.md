# inventory-identity

## Overview

Community of 39 nodes

- **Size**: 39 nodes
- **Cohesion**: 0.2798
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| UserRecord | Class | backend/models/inventory.py | 10-16 |
| UserCreate | Class | backend/models/inventory.py | 19-20 |
| AssetRecord | Class | backend/models/inventory.py | 31-40 |
| AssetCreate | Class | backend/models/inventory.py | 43-44 |
| IdentityRuleRecord | Class | backend/models/inventory.py | 58-68 |
| IdentityRuleCreate | Class | backend/models/inventory.py | 71-72 |
| ensure_pool | Function | backend/services/splunk_json_store.py | 27-34 |
| test_inventory_users_list_requires_pg_mock | Test | backend/tests/test_inventory_api.py | 29-37 |
| test_identity_rules_reorder | Test | backend/tests/test_inventory_api.py | 45-64 |
| list_users | Function | backend/services/inventory/users.py | 16-22 |
| get_user | Function | backend/services/inventory/users.py | 25-34 |
| create_user | Function | backend/services/inventory/users.py | 37-57 |
| update_user | Function | backend/services/inventory/users.py | 60-68 |
| delete_user | Function | backend/services/inventory/users.py | 71-75 |
| is_unique_violation | Function | backend/services/inventory/_db.py | 12-14 |
| raise_if_delete_missing | Function | backend/services/inventory/_db.py | 17-19 |
| dynamic_update | Function | backend/services/inventory/_db.py | 22-38 |
| read_csv | Function | backend/services/inventory/csv_seed.py | 18-20 |
| parse_bool | Function | backend/services/inventory/csv_seed.py | 23-24 |
| user_row | Function | backend/services/inventory/csv_seed.py | 27-35 |
| asset_row | Function | backend/services/inventory/csv_seed.py | 38-52 |
| rule_row | Function | backend/services/inventory/csv_seed.py | 55-67 |
| tables_empty | Function | backend/services/inventory/csv_seed.py | 70-76 |
| seed_inventory_from_csv_if_empty | Function | backend/services/inventory/csv_seed.py | 79-100 |
| InventoryNotFoundError | Class | backend/services/inventory/exceptions.py | 4-5 |
| InventoryConflictError | Class | backend/services/inventory/exceptions.py | 8-9 |
| rule_record_from_row | Function | backend/services/inventory/rules.py | 19-32 |
| list_identity_rules | Function | backend/services/inventory/rules.py | 35-41 |
| get_identity_rule | Function | backend/services/inventory/rules.py | 44-53 |
| create_identity_rule | Function | backend/services/inventory/rules.py | 56-82 |
| update_identity_rule | Function | backend/services/inventory/rules.py | 85-95 |
| delete_identity_rule | Function | backend/services/inventory/rules.py | 98-102 |
| reorder_identity_rules | Function | backend/services/inventory/rules.py | 105-119 |
| list_assets | Function | backend/services/inventory/assets.py | 18-24 |
| get_asset | Function | backend/services/inventory/assets.py | 27-36 |
| create_asset | Function | backend/services/inventory/assets.py | 39-63 |
| update_asset | Function | backend/services/inventory/assets.py | 66-74 |
| delete_asset | Function | backend/services/inventory/assets.py | 77-81 |
| ensure_inventory_schema | Function | backend/services/inventory/loader.py | 20-23 |

## Execution Flows

- **update_user** (criticality: 0.68, depth: 3)
- **create_identity_rule** (criticality: 0.68, depth: 3)
- **update_identity_rule** (criticality: 0.68, depth: 3)
- **update_asset** (criticality: 0.68, depth: 3)
- **create_user** (criticality: 0.67, depth: 2)
- **create_asset** (criticality: 0.67, depth: 2)
- **reorder_identity_rules** (criticality: 0.60, depth: 3)
- **delete_user** (criticality: 0.59, depth: 2)
- **delete_identity_rule** (criticality: 0.59, depth: 2)
- **delete_asset** (criticality: 0.59, depth: 2)
- *... and 4 more flows.*

## Dependencies

### Outgoing

- `get` (22 edge(s))
- `format` (16 edge(s))
- `acquire` (16 edge(s))
- `execute` (9 edge(s))
- `dict` (5 edge(s))
- `int` (4 edge(s))
- `patch` (4 edge(s))
- `BaseModel` (3 edge(s))
- `lower` (3 edge(s))
- `fetchrow` (3 edge(s))
- `fetch` (3 edge(s))
- `model_dump` (3 edge(s))
- `fetchval` (3 edge(s))
- `list` (2 edge(s))
- `str` (2 edge(s))

### Incoming

- `backend/models/inventory.py` (9 edge(s))
- `backend/services/inventory/csv_seed.py` (7 edge(s))
- `backend/services/inventory/rules.py` (7 edge(s))
- `backend/services/inventory/assets.py` (5 edge(s))
- `backend/services/inventory/users.py` (5 edge(s))
- `patch` (4 edge(s))
- `backend/services/inventory/_db.py` (3 edge(s))
- `backend/services/inventory/exceptions.py` (2 edge(s))
- `backend/tests/test_inventory_api.py` (2 edge(s))
- `json` (2 edge(s))
- `backend/services/inventory/loader.py` (1 edge(s))
- `backend/services/splunk_json_store.py` (1 edge(s))
- `post` (1 edge(s))
- `get` (1 edge(s))
