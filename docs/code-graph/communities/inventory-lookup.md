# inventory-lookup

## Overview

Community of 7 nodes

- **Size**: 7 nodes
- **Cohesion**: 0.2727
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| user_to_lookup | Function | backend/services/inventory/converters.py | 10-18 |
| asset_to_lookup | Function | backend/services/inventory/converters.py | 21-32 |
| rule_to_lookup | Function | backend/services/inventory/converters.py | 35-47 |
| user_record_to_lookup | Function | backend/services/inventory/converters.py | 50-51 |
| asset_record_to_lookup | Function | backend/services/inventory/converters.py | 54-55 |
| rule_record_to_lookup | Function | backend/services/inventory/converters.py | 58-59 |
| load_inventory_from_postgres | Function | backend/services/inventory/loader.py | 26-36 |

## Execution Flows

- **load_inventory_from_postgres** (criticality: 0.45, depth: 2)

## Dependencies

### Outgoing

- `model_dump` (3 edge(s))
- `str` (3 edge(s))
- `list_users` (1 edge(s))
- `list_assets` (1 edge(s))
- `list_identity_rules` (1 edge(s))

### Incoming

- `backend/services/inventory/converters.py` (6 edge(s))
- `backend/services/inventory/loader.py` (1 edge(s))
