# devtools-dashboard

## Overview

Community of 50 nodes

- **Size**: 50 nodes
- **Cohesion**: 0.3066
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| dashboard_overview | Function | backend/api/routes/dashboard.py | 21-51 |
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
| DashboardKpis | Class | backend/models/dashboard.py | 10-16 |
| CountByVerdict | Class | backend/models/dashboard.py | 32-34 |
| CountByPriority | Class | backend/models/dashboard.py | 37-39 |
| TrackSplit | Class | backend/models/dashboard.py | 42-44 |
| SystemResources | Class | backend/models/dashboard.py | 54-59 |
| DashboardOverview | Class | backend/models/dashboard.py | 76-88 |
| _compute_health_score | Function | backend/services/platform/dashboard_overview.py | 45-55 |
| build_dashboard_overview | Function | backend/services/platform/dashboard_overview.py | 127-205 |
| collect_system_resources | Function | backend/services/platform/system_resources.py | 14-28 |
| SocChatResponse | Class | backend/services/soc_rag/models.py | 99-106 |
| _ensure_pool | Function | backend/services/splunk_json_store/stats.py | 13-18 |
| fetch_record_counts_by_type | Function | backend/services/splunk_json_store/stats.py | 21-32 |
| fetch_total_records | Function | backend/services/splunk_json_store/stats.py | 35-40 |
| fetch_records_last_24h | Function | backend/services/splunk_json_store/stats.py | 43-53 |
| fetch_analyses_last_24h | Function | backend/services/splunk_json_store/stats.py | 56-67 |
| fetch_activity_by_day | Function | backend/services/splunk_json_store/stats.py | 70-185 |
| fetch_inventory_counts | Function | backend/services/splunk_json_store/stats.py | 188-194 |
| test_dashboard_overview_ok | Test | backend/tests/test_dashboard_api.py | 37-115 |
| test_build_dashboard_overview_parallel_fetch | Test | backend/tests/test_dashboard_overview_service.py | 80-140 |

## Execution Flows

- **dashboard_overview** (criticality: 0.74, depth: 8)
- **dashboard_overview** (criticality: 0.38, depth: 3)
- **classify_alert** (criticality: 0.37, depth: 2)
- **route_analysis** (criticality: 0.37, depth: 2)
- **run_agent_triage** (criticality: 0.37, depth: 2)
- **suggest_spl** (criticality: 0.37, depth: 2)
- **mcp_generate_spl** (criticality: 0.37, depth: 2)
- **mcp_call_tool** (criticality: 0.37, depth: 2)
- **run_analysis** (criticality: 0.37, depth: 2)
- **run_analysis_by_sid** (criticality: 0.37, depth: 2)
- *... and 11 more flows.*

## Dependencies

### Outgoing

- `int` (13 edge(s))
- `format` (11 edge(s))
- `get` (11 edge(s))
- `patch` (9 edge(s))
- `BaseModel` (8 edge(s))
- `acquire` (7 edge(s))
- `model_validate` (5 edge(s))
- `json` (5 edge(s))
- `fetchval` (5 edge(s))
- `perf_counter` (4 edge(s))
- `AsyncClient` (4 edge(s))
- `raise_for_status` (4 edge(s))
- `TsocTimeoutError` (4 edge(s))
- `backend/api/http_rid.py::http_rid` (3 edge(s))
- `Counter` (3 edge(s))

### Incoming

- `patch` (9 edge(s))
- `backend/services/splunk_json_store/stats.py` (7 edge(s))
- `backend/models/dashboard.py` (6 edge(s))
- `backend/services/platform/dashboard_overview.py` (2 edge(s))
- `perf_counter` (2 edge(s))
- `backend/api/routes/dashboard.py` (1 edge(s))
- `backend/devtools/async_client.py` (1 edge(s))
- `backend/devtools/client.py::TsocSdkClient.dashboard_overview` (1 edge(s))
- `backend/services/platform/system_resources.py` (1 edge(s))
- `backend/devtools/client.py::TsocSdkClient.soc_chat` (1 edge(s))
- `backend/services/soc_rag/models.py` (1 edge(s))
- `backend/tests/test_dashboard_api.py` (1 edge(s))
- `backend/models/triage.py::TriageOutcome` (1 edge(s))
- `get` (1 edge(s))
- `json` (1 edge(s))
