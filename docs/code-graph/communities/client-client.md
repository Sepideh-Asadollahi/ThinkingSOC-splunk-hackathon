# client-client

## Overview

Community of 9 nodes

- **Size**: 9 nodes
- **Cohesion**: 0.1700
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| SplunkRestClient | Class | backend/splunk/client/rest_client.py | 29-305 |
| __init__ | Function | backend/splunk/client/rest_client.py | 30-34 |
| _client | Function | backend/splunk/client/rest_client.py | 36-37 |
| login | Function | backend/splunk/client/rest_client.py | 39-70 |
| _auth_headers | Function | backend/splunk/client/rest_client.py | 72-73 |
| get_job | Function | backend/splunk/client/rest_client.py | 75-98 |
| fetch_all_results | Function | backend/splunk/client/rest_client.py | 100-146 |
| oneshot_search | Function | backend/splunk/client/rest_client.py | 148-221 |
| parse_spl | Function | backend/splunk/client/rest_client.py | 223-305 |

## Execution Flows

- **login** (criticality: 0.48, depth: 1)
- **get_job** (criticality: 0.44, depth: 1)
- **fetch_all_results** (criticality: 0.44, depth: 1)
- **oneshot_search** (criticality: 0.44, depth: 1)
- **parse_spl** (criticality: 0.44, depth: 1)

## Dependencies

### Outgoing

- `warning` (14 edge(s))
- `len` (8 edge(s))
- `get` (7 edge(s))
- `format` (6 edge(s))
- `quote` (6 edge(s))
- `urljoin` (5 edge(s))
- `raise_for_status` (5 edge(s))
- `json` (5 edge(s))
- `info` (3 edge(s))
- `mgmt_netloc` (3 edge(s))
- `debug` (2 edge(s))
- `ValueError` (2 edge(s))
- `post` (2 edge(s))
- `str` (2 edge(s))
- `join` (2 edge(s))

### Incoming

- `backend/splunk/client/rest_client.py` (1 edge(s))
