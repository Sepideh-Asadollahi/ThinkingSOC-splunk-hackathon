# inventory-dict

## Overview

Community of 7 nodes

- **Size**: 7 nodes
- **Cohesion**: 0.2857
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| user_to_dict | Function | backend/services/inventory/converters.py | 10-18 |
| asset_to_dict | Function | backend/services/inventory/converters.py | 21-32 |
| relationship_to_dict | Function | backend/services/inventory/converters.py | 35-41 |
| user_record_to_dict | Function | backend/services/inventory/converters.py | 44-45 |
| asset_record_to_dict | Function | backend/services/inventory/converters.py | 48-49 |
| relationship_record_to_dict | Function | backend/services/inventory/converters.py | 52-53 |
| load_inventory_from_postgres | Function | backend/services/inventory/loader.py | 24-34 |

## Execution Flows

- **load_inventory_from_postgres** (criticality: 0.45, depth: 2)

## Dependencies

### Outgoing

- `model_dump` (3 edge(s))
- `str` (2 edge(s))
- `list_users` (1 edge(s))
- `list_assets` (1 edge(s))
- `list_relationships` (1 edge(s))

### Incoming

- `backend/services/inventory/converters.py` (6 edge(s))
- `backend/services/inventory/loader.py` (1 edge(s))
