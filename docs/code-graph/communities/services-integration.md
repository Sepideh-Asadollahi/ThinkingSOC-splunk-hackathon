# services-integration

## Overview

Community of 16 nodes

- **Size**: 16 nodes
- **Cohesion**: 0.2014
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| IntegrationSettingRecord | Class | backend/models/integration_settings.py | 22-31 |
| _normalize_category | Function | backend/services/integration_settings.py | 316-330 |
| _default_store | Function | backend/services/integration_settings.py | 333-334 |
| _read_store | Function | backend/services/integration_settings.py | 337-355 |
| _write_store | Function | backend/services/integration_settings.py | 358-360 |
| load_setting_overrides | Function | backend/services/integration_settings.py | 363-378 |
| _coerce_value | Function | backend/services/integration_settings.py | 381-393 |
| _serialize_value | Function | backend/services/integration_settings.py | 396-401 |
| _field_value | Function | backend/services/integration_settings.py | 404-405 |
| _builtin_record | Function | backend/services/integration_settings.py | 408-433 |
| _custom_record | Function | backend/services/integration_settings.py | 436-451 |
| list_integration_settings | Function | backend/services/integration_settings.py | 454-466 |
| get_integration_setting | Function | backend/services/integration_settings.py | 469-473 |
| create_integration_setting | Function | backend/services/integration_settings.py | 476-499 |
| update_integration_setting | Function | backend/services/integration_settings.py | 502-548 |
| delete_integration_setting | Function | backend/services/integration_settings.py | 551-574 |

## Execution Flows

- **get_integration_setting** (criticality: 0.46, depth: 3)
- **create_integration_setting** (criticality: 0.45, depth: 2)
- **update_integration_setting** (criticality: 0.45, depth: 2)
- **delete_integration_setting** (criticality: 0.37, depth: 2)

## Dependencies

### Outgoing

- `get` (29 edge(s))
- `str` (15 edge(s))
- `strip` (8 edge(s))
- `isinstance` (6 edge(s))
- `bool` (5 edge(s))
- `append` (4 edge(s))
- `KeyError` (4 edge(s))
- `ValueError` (3 edge(s))
- `dict` (3 edge(s))
- `items` (2 edge(s))
- `list` (2 edge(s))
- `BaseModel` (1 edge(s))
- `lower` (1 edge(s))
- `int` (1 edge(s))
- `float` (1 edge(s))

### Incoming

- `backend/services/integration_settings.py` (15 edge(s))
- `backend/models/integration_settings.py` (1 edge(s))
