# devtools-triage

## Overview

Community of 87 nodes

- **Size**: 87 nodes
- **Cohesion**: 0.3642
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| AsyncTsocSdkClient | Class | backend/devtools/async_client.py | 37-283 |
| __init__ | Function | backend/devtools/async_client.py | 38-51 |
| _headers | Function | backend/devtools/async_client.py | 53-56 |
| _to_payload | Function | backend/devtools/async_client.py | 59-62 |
| _raise_api_error | Function | backend/devtools/async_client.py | 64-72 |
| _post_model | Function | backend/devtools/async_client.py | 74-100 |
| _get_raw | Function | backend/devtools/async_client.py | 102-113 |
| _get_model | Function | backend/devtools/async_client.py | 115-117 |
| _post_raw | Function | backend/devtools/async_client.py | 119-130 |
| classify_alert | Function | backend/devtools/async_client.py | 134-138 |
| route_analysis | Function | backend/devtools/async_client.py | 140-144 |
| run_agent_triage | Function | backend/devtools/async_client.py | 146-150 |
| suggest_spl | Function | backend/devtools/async_client.py | 152-156 |
| mcp_status | Function | backend/devtools/async_client.py | 158-164 |
| mcp_generate_spl | Function | backend/devtools/async_client.py | 168-173 |
| mcp_call_tool | Function | backend/devtools/async_client.py | 175-180 |
| run_analysis | Function | backend/devtools/async_client.py | 184-189 |
| run_analysis_by_sid | Function | backend/devtools/async_client.py | 191-196 |
| search_events | Function | backend/devtools/async_client.py | 200-211 |
| get_event | Function | backend/devtools/async_client.py | 213-215 |
| dashboard_overview | Function | backend/devtools/async_client.py | 217-219 |
| run_observability | Function | backend/devtools/async_client.py | 223-228 |
| run_observability_by_sid | Function | backend/devtools/async_client.py | 230-235 |
| soc_chat | Function | backend/devtools/async_client.py | 239-244 |
| soc_chat_status | Function | backend/devtools/async_client.py | 246-248 |
| investigation_timeline | Function | backend/devtools/async_client.py | 252-254 |
| analyst_actions | Function | backend/devtools/async_client.py | 256-258 |
| add_analyst_action | Function | backend/devtools/async_client.py | 260-266 |
| triage_queue | Function | backend/devtools/async_client.py | 270-277 |
| health | Function | backend/devtools/async_client.py | 281-283 |
| TsocSdkClient | Class | backend/devtools/client.py | 37-281 |
| __init__ | Function | backend/devtools/client.py | 38-51 |
| _headers | Function | backend/devtools/client.py | 53-56 |
| _to_payload | Function | backend/devtools/client.py | 59-62 |
| _raise_api_error | Function | backend/devtools/client.py | 64-72 |
| _post_model | Function | backend/devtools/client.py | 74-98 |
| _get_raw | Function | backend/devtools/client.py | 100-111 |
| _get_model | Function | backend/devtools/client.py | 113-115 |
| _post_raw | Function | backend/devtools/client.py | 117-128 |
| classify_alert | Function | backend/devtools/client.py | 132-136 |
| route_analysis | Function | backend/devtools/client.py | 138-142 |
| run_agent_triage | Function | backend/devtools/client.py | 144-148 |
| suggest_spl | Function | backend/devtools/client.py | 150-154 |
| mcp_status | Function | backend/devtools/client.py | 156-162 |
| mcp_generate_spl | Function | backend/devtools/client.py | 166-171 |
| mcp_call_tool | Function | backend/devtools/client.py | 173-178 |
| run_analysis | Function | backend/devtools/client.py | 182-187 |
| run_analysis_by_sid | Function | backend/devtools/client.py | 189-194 |
| search_events | Function | backend/devtools/client.py | 198-209 |
| get_event | Function | backend/devtools/client.py | 211-213 |

*... and 37 more members.*

## Execution Flows

- **run_analysis** (criticality: 0.76, depth: 6)
- **dashboard_overview** (criticality: 0.74, depth: 8)
- **list_triage_queue** (criticality: 0.73, depth: 6)
- **run_observability_analysis** (criticality: 0.71, depth: 5)
- **compute_triage_from_judge_verdict** (criticality: 0.55, depth: 4)
- **compute_triage_from_ops_judge** (criticality: 0.55, depth: 4)
- **dashboard_overview** (criticality: 0.38, depth: 3)
- **dashboard_overview** (criticality: 0.38, depth: 3)
- **classify_alert** (criticality: 0.37, depth: 2)
- **route_analysis** (criticality: 0.37, depth: 2)
- *... and 36 more flows.*

## Dependencies

### Outgoing

- `get` (24 edge(s))
- `format` (20 edge(s))
- `int` (15 edge(s))
- `patch` (11 edge(s))
- `BaseModel` (10 edge(s))
- `json` (9 edge(s))
- `raise_for_status` (8 edge(s))
- `TsocTimeoutError` (8 edge(s))
- `model_validate` (7 edge(s))
- `acquire` (7 edge(s))
- `max` (5 edge(s))
- `isinstance` (5 edge(s))
- `fetchval` (5 edge(s))
- `AsyncClient` (4 edge(s))
- `range` (4 edge(s))

### Incoming

- `patch` (11 edge(s))
- `backend/services/splunk_json_store/stats.py` (7 edge(s))
- `backend/models/dashboard.py` (6 edge(s))
- `backend/services/platform/dashboard_overview.py` (3 edge(s))
- `backend/services/triage/triage_queue.py` (3 edge(s))
- `backend/tests/test_triage_queue.py` (3 edge(s))
- `perf_counter` (2 edge(s))
- `range` (2 edge(s))
- `len` (2 edge(s))
- `issubset` (2 edge(s))
- `backend/devtools/async_client.py` (1 edge(s))
- `backend/devtools/client.py` (1 edge(s))
- `backend/models/triage.py` (1 edge(s))
- `backend/services/triage/triage_priority.py::compute_triage_outcome` (1 edge(s))
- `backend/api/routes/dashboard.py::dashboard_overview` (1 edge(s))
