# client-spl

## Overview

Community of 13 nodes

- **Size**: 13 nodes
- **Cohesion**: 0.1137
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _httpx_error_detail | Function | backend/splunk/client/rest_client.py | 34-62 |
| SplunkRestClient | Class | backend/splunk/client/rest_client.py | 65-522 |
| __init__ | Function | backend/splunk/client/rest_client.py | 66-70 |
| _client | Function | backend/splunk/client/rest_client.py | 72-73 |
| login | Function | backend/splunk/client/rest_client.py | 75-106 |
| _auth_headers | Function | backend/splunk/client/rest_client.py | 108-109 |
| predict_spl_via_ui_path | Function | backend/splunk/client/rest_client.py | 111-263 |
| get_job | Function | backend/splunk/client/rest_client.py | 265-288 |
| fetch_all_results | Function | backend/splunk/client/rest_client.py | 290-336 |
| oneshot_search | Function | backend/splunk/client/rest_client.py | 338-418 |
| _spl_query_for_parser | Function | backend/splunk/client/rest_client.py | 421-433 |
| parse_spl | Function | backend/splunk/client/rest_client.py | 435-522 |
| _find_chat_entry_by_id | Function | backend/splunk/client/rest_client.py | 525-538 |

## Execution Flows

- **login** (criticality: 0.48, depth: 1)
- **parse_spl** (criticality: 0.48, depth: 1)
- **predict_spl_via_ui_path** (criticality: 0.46, depth: 1)
- **get_job** (criticality: 0.44, depth: 1)
- **fetch_all_results** (criticality: 0.44, depth: 1)
- **oneshot_search** (criticality: 0.44, depth: 1)

## Dependencies

### Outgoing

- `get` (20 edge(s))
- `warning` (14 edge(s))
- `str` (13 edge(s))
- `format` (12 edge(s))
- `len` (12 edge(s))
- `isinstance` (11 edge(s))
- `quote` (9 edge(s))
- `json` (8 edge(s))
- `info` (8 edge(s))
- `urljoin` (7 edge(s))
- `raise_for_status` (7 edge(s))
- `strip` (6 edge(s))
- `RuntimeError` (6 edge(s))
- `debug` (5 edge(s))
- `post` (4 edge(s))

### Incoming

- `backend/splunk/client/rest_client.py` (3 edge(s))
