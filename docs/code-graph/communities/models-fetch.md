# models-fetch

## Overview

Community of 28 nodes

- **Size**: 28 nodes
- **Cohesion**: 0.2315
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| TriageOutcome | Class | backend/models/triage.py | 39-55 |
| DashboardKpis | Class | backend/models/dashboard.py | 10-16 |
| CountByVerdict | Class | backend/models/dashboard.py | 32-34 |
| CountByPriority | Class | backend/models/dashboard.py | 37-39 |
| TrackSplit | Class | backend/models/dashboard.py | 42-44 |
| DashboardIntegrations | Class | backend/models/dashboard.py | 47-51 |
| SystemResources | Class | backend/models/dashboard.py | 54-59 |
| DashboardOverview | Class | backend/models/dashboard.py | 76-88 |
| test_dashboard_overview_ok | Test | backend/tests/test_dashboard_api.py | 37-115 |
| test_build_triage_queue_skips_invalid_payload | Test | backend/tests/test_triage_queue.py | 29-73 |
| test_build_triage_queue_all_includes_both_tracks_not_global_top_n | Test | backend/tests/test_triage_queue.py | 77-137 |
| _row | Function | backend/tests/test_triage_queue.py | 82-103 |
| _compute_health_score | Function | backend/services/platform/dashboard_overview.py | 36-46 |
| _neo4j_reachable | Function | backend/services/platform/dashboard_overview.py | 49-60 |
| _collect_triage_items | Function | backend/services/platform/dashboard_overview.py | 63-64 |
| _integrations_status | Function | backend/services/platform/dashboard_overview.py | 67-76 |
| build_dashboard_overview | Function | backend/services/platform/dashboard_overview.py | 79-149 |
| collect_system_resources | Function | backend/services/platform/system_resources.py | 14-28 |
| _ensure_pool | Function | backend/services/splunk_json_store/stats.py | 13-18 |
| fetch_record_counts_by_type | Function | backend/services/splunk_json_store/stats.py | 21-32 |
| fetch_total_records | Function | backend/services/splunk_json_store/stats.py | 35-40 |
| fetch_records_last_24h | Function | backend/services/splunk_json_store/stats.py | 43-53 |
| fetch_analyses_last_24h | Function | backend/services/splunk_json_store/stats.py | 56-67 |
| fetch_activity_by_day | Function | backend/services/splunk_json_store/stats.py | 70-185 |
| fetch_inventory_counts | Function | backend/services/splunk_json_store/stats.py | 188-194 |
| queue_item_from_row | Function | backend/services/triage/triage_queue.py | 26-41 |
| record_types_for_track | Function | backend/services/triage/triage_queue.py | 44-49 |
| build_triage_queue_items | Function | backend/services/triage/triage_queue.py | 52-89 |

## Execution Flows

- **splunk_ingest** (criticality: 0.77, depth: 9)
- **run_analysis** (criticality: 0.76, depth: 6)
- **agent_triage_endpoint** (criticality: 0.76, depth: 8)
- **dashboard_overview** (criticality: 0.74, depth: 8)
- **list_triage_queue** (criticality: 0.73, depth: 6)
- **run_observability_analysis** (criticality: 0.71, depth: 5)
- **compute_triage_from_judge_verdict** (criticality: 0.55, depth: 4)
- **compute_triage_from_ops_judge** (criticality: 0.55, depth: 4)

## Dependencies

### Outgoing

- `get` (18 edge(s))
- `int` (13 edge(s))
- `BaseModel` (8 edge(s))
- `acquire` (7 edge(s))
- `fetchval` (5 edge(s))
- `backend/services/splunk_json_store/__init__.py::splunk_store_configured` (3 edge(s))
- `Counter` (3 edge(s))
- `str` (3 edge(s))
- `round` (3 edge(s))
- `model_validate` (3 edge(s))
- `fetch` (3 edge(s))
- `isinstance` (3 edge(s))
- `len` (3 edge(s))
- `patch` (3 edge(s))
- `bool` (2 edge(s))

### Incoming

- `backend/models/dashboard.py` (7 edge(s))
- `backend/services/splunk_json_store/stats.py` (7 edge(s))
- `backend/services/platform/dashboard_overview.py` (5 edge(s))
- `backend/services/triage/triage_queue.py` (3 edge(s))
- `patch` (3 edge(s))
- `backend/tests/test_triage_queue.py` (3 edge(s))
- `range` (2 edge(s))
- `len` (2 edge(s))
- `issubset` (2 edge(s))
- `backend/devtools/async_client.py::AsyncTsocSdkClient.dashboard_overview` (1 edge(s))
- `backend/devtools/client.py::TsocSdkClient.dashboard_overview` (1 edge(s))
- `backend/models/triage.py` (1 edge(s))
- `backend/services/triage/triage_priority.py::compute_triage_outcome` (1 edge(s))
- `backend/api/routes/dashboard.py::dashboard_overview` (1 edge(s))
- `backend/services/platform/system_resources.py` (1 edge(s))
