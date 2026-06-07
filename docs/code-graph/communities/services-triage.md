# services-triage

## Overview

Community of 43 nodes

- **Size**: 43 nodes
- **Cohesion**: 0.2714
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| TriageFactor | Class | backend/models/triage.py | 14-22 |
| TriageReport | Class | backend/models/triage.py | 25-36 |
| TriageOutcome | Class | backend/models/triage.py | 39-55 |
| DashboardKpis | Class | backend/models/dashboard.py | 10-16 |
| CountByVerdict | Class | backend/models/dashboard.py | 32-34 |
| CountByPriority | Class | backend/models/dashboard.py | 37-39 |
| TrackSplit | Class | backend/models/dashboard.py | 42-44 |
| DashboardIntegrations | Class | backend/models/dashboard.py | 47-50 |
| DashboardOverview | Class | backend/models/dashboard.py | 67-78 |
| _queue_item_from_row | Function | backend/services/dashboard_overview.py | 39-53 |
| _compute_health_score | Function | backend/services/dashboard_overview.py | 56-64 |
| _collect_triage_items | Function | backend/services/dashboard_overview.py | 67-85 |
| _integrations_status | Function | backend/services/dashboard_overview.py | 88-95 |
| build_dashboard_overview | Function | backend/services/dashboard_overview.py | 98-167 |
| _norm_token | Function | backend/services/triage_priority.py | 30-34 |
| map_judge_verdict_to_review | Function | backend/services/triage_priority.py | 37-47 |
| confidence_to_score | Function | backend/services/triage_priority.py | 50-58 |
| _priority_weight | Function | backend/services/triage_priority.py | 61-69 |
| _impact_weight | Function | backend/services/triage_priority.py | 72-80 |
| _inventory_risk_bonus | Function | backend/services/triage_priority.py | 83-98 |
| _enrichment_penalty | Function | backend/services/triage_priority.py | 101-109 |
| investigation_priority_from_score | Function | backend/services/triage_priority.py | 112-119 |
| _base_score_for_review | Function | backend/services/triage_priority.py | 122-127 |
| _apply_conviction_gate | Function | backend/services/triage_priority.py | 130-136 |
| _recommended_action | Function | backend/services/triage_priority.py | 157-180 |
| _why_verdict_text | Function | backend/services/triage_priority.py | 183-208 |
| _why_priority_text | Function | backend/services/triage_priority.py | 211-220 |
| _build_triage_report | Function | backend/services/triage_priority.py | 223-260 |
| compute_triage_outcome | Function | backend/services/triage_priority.py | 263-438 |
| compute_triage_from_judge_verdict | Function | backend/services/triage_priority.py | 481-503 |
| compute_triage_from_ops_judge | Function | backend/services/triage_priority.py | 506-521 |
| test_dashboard_overview_ok | Test | backend/tests/test_dashboard_api.py | 37-105 |
| test_map_false_positive | Test | backend/tests/test_triage_priority.py | 56-57 |
| test_map_true_positive | Test | backend/tests/test_triage_priority.py | 60-61 |
| test_investigation_priority_buckets | Test | backend/tests/test_triage_priority.py | 102-106 |
| test_observability_track | Test | backend/tests/test_triage_priority.py | 121-130 |
| _ensure_pool | Function | backend/services/splunk_json_store/stats.py | 13-18 |
| fetch_record_counts_by_type | Function | backend/services/splunk_json_store/stats.py | 21-32 |
| fetch_total_records | Function | backend/services/splunk_json_store/stats.py | 35-40 |
| fetch_records_last_24h | Function | backend/services/splunk_json_store/stats.py | 43-53 |
| fetch_analyses_last_24h | Function | backend/services/splunk_json_store/stats.py | 56-67 |
| fetch_activity_by_day | Function | backend/services/splunk_json_store/stats.py | 70-135 |
| fetch_inventory_counts | Function | backend/services/splunk_json_store/stats.py | 138-144 |

## Execution Flows

- **splunk_ingest** (criticality: 0.74, depth: 7)
- **run_analysis** (criticality: 0.74, depth: 5)
- **agent_triage_endpoint** (criticality: 0.73, depth: 6)
- **dashboard_overview** (criticality: 0.73, depth: 7)
- **list_triage_queue** (criticality: 0.72, depth: 5)
- **run_observability_analysis** (criticality: 0.71, depth: 5)
- **compute_triage_from_judge_verdict** (criticality: 0.55, depth: 4)
- **compute_triage_from_ops_judge** (criticality: 0.55, depth: 4)

## Dependencies

### Outgoing

- `append` (22 edge(s))
- `get` (19 edge(s))
- `format` (15 edge(s))
- `int` (14 edge(s))
- `BaseModel` (9 edge(s))
- `acquire` (6 edge(s))
- `fetchval` (5 edge(s))
- `replace` (5 edge(s))
- `isinstance` (3 edge(s))
- `min` (3 edge(s))
- `Counter` (3 edge(s))
- `str` (3 edge(s))
- `model_validate` (3 edge(s))
- `join` (3 edge(s))
- `strip` (3 edge(s))

### Incoming

- `backend/services/triage_priority.py` (17 edge(s))
- `backend/services/splunk_json_store/stats.py` (7 edge(s))
- `backend/models/dashboard.py` (6 edge(s))
- `backend/services/dashboard_overview.py` (5 edge(s))
- `backend/tests/test_triage_priority.py` (4 edge(s))
- `backend/models/triage.py` (3 edge(s))
- `backend/api/routes/dashboard.py::dashboard_overview` (1 edge(s))
- `backend/services/triage_priority.py::compute_triage_from_soc` (1 edge(s))
- `backend/services/triage_priority.py::compute_triage_from_observability` (1 edge(s))
- `backend/services/triage_priority.py::triage_from_stored_payload` (1 edge(s))
- `backend/tests/test_dashboard_api.py` (1 edge(s))
- `patch` (1 edge(s))
- `get` (1 edge(s))
- `json` (1 edge(s))
