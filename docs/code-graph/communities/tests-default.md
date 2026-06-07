# tests-default

## Overview

Community of 30 nodes

- **Size**: 30 nodes
- **Cohesion**: 0.3196
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| UserCreate | Class | backend/models/inventory.py | 19-20 |
| AssetCreate | Class | backend/models/inventory.py | 43-44 |
| RelationshipCreate | Class | backend/models/inventory.py | 65-66 |
| _demo_users | Function | backend/tests/test_default_relationships.py | 16-30 |
| _demo_assets | Function | backend/tests/test_default_relationships.py | 33-52 |
| test_build_default_links_owner_user_id | Test | backend/tests/test_default_relationships.py | 55-62 |
| test_build_default_links_owner_team_to_department | Test | backend/tests/test_default_relationships.py | 65-70 |
| test_build_default_skips_unknown_owner | Test | backend/tests/test_default_relationships.py | 73-76 |
| test_build_default_one_relationship_per_pair | Test | backend/tests/test_default_relationships.py | 79-82 |
| test_merge_explicit_overrides_default_description | Test | backend/tests/test_default_relationships.py | 85-98 |
| test_merge_combines_disjoint_pairs | Test | backend/tests/test_default_relationships.py | 101-112 |
| _mock_pool | Function | backend/tests/test_default_relationships.py | 115-128 |
| _AcquireCtx | Class | backend/tests/test_default_relationships.py | 119-124 |
| __aenter__ | Function | backend/tests/test_default_relationships.py | 120-121 |
| __aexit__ | Function | backend/tests/test_default_relationships.py | 123-124 |
| test_ensure_default_relationships_skips_when_links_exist | Test | backend/tests/test_default_relationships.py | 132-136 |
| test_ensure_default_relationships_creates_from_inventory | Test | backend/tests/test_default_relationships.py | 140-166 |
| test_demo_csv_rows_produce_expected_defaults | Test | backend/tests/test_default_relationships.py | 169-179 |
| read_csv | Function | backend/services/inventory/csv_seed.py | 22-24 |
| user_row | Function | backend/services/inventory/csv_seed.py | 27-35 |
| asset_row | Function | backend/services/inventory/csv_seed.py | 38-52 |
| relationship_row | Function | backend/services/inventory/csv_seed.py | 55-61 |
| tables_empty | Function | backend/services/inventory/csv_seed.py | 64-70 |
| ensure_default_relationships | Function | backend/services/inventory/csv_seed.py | 73-102 |
| seed_inventory_from_csv_if_empty | Function | backend/services/inventory/csv_seed.py | 105-141 |
| _norm | Function | backend/services/inventory/default_relationships.py | 14-17 |
| _relationship_id | Function | backend/services/inventory/default_relationships.py | 20-22 |
| _pick_user_for_asset | Function | backend/services/inventory/default_relationships.py | 25-46 |
| build_default_relationships | Function | backend/services/inventory/default_relationships.py | 49-92 |
| merge_relationship_lists | Function | backend/services/inventory/default_relationships.py | 95-109 |

## Execution Flows

- **seed_inventory_from_csv_if_empty** (criticality: 0.52, depth: 2)

## Dependencies

### Outgoing

- `get` (25 edge(s))
- `len` (8 edge(s))
- `fetchval` (6 edge(s))
- `lower` (5 edge(s))
- `patch` (5 edge(s))
- `AsyncMock` (4 edge(s))
- `AssetRecord` (2 edge(s))
- `UserRecord` (2 edge(s))
- `strip` (2 edge(s))
- `int` (2 edge(s))
- `backend/services/splunk_json_store/__init__.py::ensure_pool` (2 edge(s))
- `acquire` (2 edge(s))
- `create_relationship` (2 edge(s))
- `info` (2 edge(s))
- `list` (2 edge(s))

### Incoming

- `backend/tests/test_default_relationships.py` (13 edge(s))
- `backend/services/inventory/csv_seed.py` (7 edge(s))
- `backend/services/inventory/default_relationships.py` (5 edge(s))
- `len` (5 edge(s))
- `patch` (5 edge(s))
- `backend/models/inventory.py` (3 edge(s))
- `read_csv` (2 edge(s))
- `AsyncMock` (2 edge(s))
- `set` (1 edge(s))
- `user_row` (1 edge(s))
- `asset_row` (1 edge(s))
- `UserRecord` (1 edge(s))
- `AssetRecord` (1 edge(s))
- `assert_awaited_once` (1 edge(s))
