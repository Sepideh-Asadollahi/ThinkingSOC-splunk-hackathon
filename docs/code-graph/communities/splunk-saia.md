# splunk-saia

## Overview

Community of 18 nodes

- **Size**: 18 nodes
- **Cohesion**: 0.2200
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| kv_needs_repair | Function | backend/splunk/saia_config_repair.py | 47-50 |
| _decode_jwt_payload | Function | backend/splunk/saia_config_repair.py | 53-63 |
| _infer_tenant_hostname | Function | backend/splunk/saia_config_repair.py | 66-67 |
| parse_saia_log_defaults | Function | backend/splunk/saia_config_repair.py | 70-98 |
| merge_saia_configs | Function | backend/splunk/saia_config_repair.py | 101-131 |
| _splunk_cmd_python | Function | backend/splunk/saia_config_repair.py | 134-136 |
| _refresh_token_sync | Function | backend/splunk/saia_config_repair.py | 139-161 |
| _SaiaKvClient | Class | backend/splunk/saia_config_repair.py | 164-217 |
| __init__ | Function | backend/splunk/saia_config_repair.py | 165-168 |
| _headers | Function | backend/splunk/saia_config_repair.py | 170-171 |
| read_kv_configs | Function | backend/splunk/saia_config_repair.py | 173-186 |
| write_kv_entry | Function | backend/splunk/saia_config_repair.py | 188-198 |
| write_conf_stanza | Function | backend/splunk/saia_config_repair.py | 200-210 |
| reload_saia_app | Function | backend/splunk/saia_config_repair.py | 212-217 |
| repair_saia_cloud_configs | Function | backend/splunk/saia_config_repair.py | 220-247 |
| ensure_saia_cloud_configs | Function | backend/splunk/saia_config_repair.py | 250-278 |
| test_kv_needs_repair_empty_tenant | Test | backend/tests/test_saia_config_repair.py | 16-28 |
| test_merge_saia_configs_from_jwt | Test | backend/tests/test_saia_config_repair.py | 31-51 |

## Execution Flows

- **_refresh_token_sync** (criticality: 0.48, depth: 1)
- **ensure_saia_cloud_configs** (criticality: 0.38, depth: 3)

## Dependencies

### Outgoing

- `get` (18 edge(s))
- `format` (13 edge(s))
- `str` (9 edge(s))
- `RuntimeError` (8 edge(s))
- `strip` (8 edge(s))
- `urljoin` (4 edge(s))
- `AsyncClient` (4 edge(s))
- `rstrip` (3 edge(s))
- `post` (3 edge(s))
- `len` (3 edge(s))
- `isinstance` (2 edge(s))
- `split` (2 edge(s))
- `is_file` (2 edge(s))
- `splitlines` (2 edge(s))
- `getattr` (2 edge(s))

### Incoming

- `backend/splunk/saia_config_repair.py` (10 edge(s))
- `backend/tests/test_saia_config_repair.py` (2 edge(s))
- `setattr` (1 edge(s))
