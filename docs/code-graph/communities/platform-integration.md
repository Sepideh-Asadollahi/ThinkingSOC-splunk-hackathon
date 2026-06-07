# platform-integration

## Overview

Community of 19 nodes

- **Size**: 19 nodes
- **Cohesion**: 0.2174
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| IntegrationSettingRecord | Class | backend/models/integration_settings.py | 22-31 |
| _normalize_category | Function | backend/services/platform/integration_settings.py | 349-363 |
| _default_store | Function | backend/services/platform/integration_settings.py | 366-367 |
| _parse_store_file | Function | backend/services/platform/integration_settings.py | 370-388 |
| _merge_store_data | Function | backend/services/platform/integration_settings.py | 391-405 |
| _migrate_legacy_store_if_needed | Function | backend/services/platform/integration_settings.py | 408-420 |
| _read_store | Function | backend/services/platform/integration_settings.py | 423-425 |
| _write_store | Function | backend/services/platform/integration_settings.py | 428-430 |
| load_setting_overrides | Function | backend/services/platform/integration_settings.py | 433-448 |
| _coerce_value | Function | backend/services/platform/integration_settings.py | 451-463 |
| _serialize_value | Function | backend/services/platform/integration_settings.py | 466-471 |
| _field_value | Function | backend/services/platform/integration_settings.py | 474-475 |
| _builtin_record | Function | backend/services/platform/integration_settings.py | 478-503 |
| _custom_record | Function | backend/services/platform/integration_settings.py | 506-521 |
| list_integration_settings | Function | backend/services/platform/integration_settings.py | 524-535 |
| get_integration_setting | Function | backend/services/platform/integration_settings.py | 538-542 |
| create_integration_setting | Function | backend/services/platform/integration_settings.py | 545-568 |
| update_integration_setting | Function | backend/services/platform/integration_settings.py | 571-615 |
| delete_integration_setting | Function | backend/services/platform/integration_settings.py | 618-631 |

## Execution Flows

- **get_integration_setting** (criticality: 0.47, depth: 4)
- **create_integration_setting** (criticality: 0.46, depth: 3)
- **update_integration_setting** (criticality: 0.46, depth: 3)
- **delete_integration_setting** (criticality: 0.38, depth: 3)

## Dependencies

### Outgoing

- `get` (30 edge(s))
- `str` (17 edge(s))
- `strip` (8 edge(s))
- `isinstance` (7 edge(s))
- `bool` (5 edge(s))
- `ValueError` (4 edge(s))
- `list` (3 edge(s))
- `append` (3 edge(s))
- `KeyError` (3 edge(s))
- `is_file` (2 edge(s))
- `items` (2 edge(s))
- `dict` (2 edge(s))
- `BaseModel` (1 edge(s))
- `lower` (1 edge(s))
- `int` (1 edge(s))

### Incoming

- `backend/services/platform/integration_settings.py` (18 edge(s))
- `backend/models/integration_settings.py` (1 edge(s))
