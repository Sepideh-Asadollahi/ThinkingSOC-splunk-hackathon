# tests-row

## Overview

Community of 316 nodes

- **Size**: 316 nodes
- **Cohesion**: 0.2849
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| AppError | Class | backend/api/app_errors.py | 12-87 |
| __str__ | Function | backend/api/app_errors.py | 22-25 |
| bad_request | Function | backend/api/app_errors.py | 28-42 |
| not_found | Function | backend/api/app_errors.py | 45-46 |
| conflict | Function | backend/api/app_errors.py | 49-50 |
| service_unavailable | Function | backend/api/app_errors.py | 53-67 |
| upstream_error | Function | backend/api/app_errors.py | 70-87 |
| splunk_job_not_found | Function | backend/api/app_errors.py | 90-103 |
| splunk_rest_error | Function | backend/api/app_errors.py | 106-131 |
| map_exception | Function | backend/api/app_errors.py | 134-211 |
| _extract_bearer_token | Function | backend/api/deps.py | 18-21 |
| check_ingest_bearer | Function | backend/api/deps.py | 24-35 |
| check_admin_bearer | Function | backend/api/deps.py | 38-50 |
| rate_limit_sensitive | Function | backend/api/deps.py | 53-78 |
| build_error_body | Function | backend/api/exception_handlers.py | 31-54 |
| _detail_to_message | Function | backend/api/exception_handlers.py | 57-70 |
| app_error_handler | Function | backend/api/exception_handlers.py | 73-93 |
| http_exception_handler | Function | backend/api/exception_handlers.py | 96-117 |
| _format_validation_errors | Function | backend/api/exception_handlers.py | 120-138 |
| request_validation_handler | Function | backend/api/exception_handlers.py | 141-154 |
| unhandled_exception_handler | Function | backend/api/exception_handlers.py | 157-185 |
| register_exception_handlers | Function | backend/api/exception_handlers.py | 188-192 |
| http_rid | Function | backend/api/http_rid.py | 8-9 |
| admin_org_gap_suggest | Function | backend/api/routes/admin_org.py | 27-56 |
| agent_triage_endpoint | Function | backend/api/routes/agents.py | 24-54 |
| classify_alert_endpoint | Function | backend/api/routes/analysis.py | 45-73 |
| run_soc_analysis_endpoint | Function | backend/api/routes/analysis.py | 81-159 |
| run_routed_analysis_endpoint | Function | backend/api/routes/analysis.py | 167-344 |
| run_soc_analysis_batch_by_sid_endpoint | Function | backend/api/routes/analysis.py | 352-427 |
| assistant_spl_suggest | Function | backend/api/routes/assistant.py | 23-52 |
| dashboard_overview | Function | backend/api/routes/dashboard.py | 21-51 |
| splunk_ingest | Function | backend/api/routes/ingest.py | 42-283 |
| splunk_ingest_debug | Function | backend/api/routes/ingest.py | 287-329 |
| list_settings_endpoint | Function | backend/api/routes/integrations.py | 22-25 |
| get_setting_endpoint | Function | backend/api/routes/integrations.py | 29-36 |
| create_setting_endpoint | Function | backend/api/routes/integrations.py | 40-50 |
| update_setting_endpoint | Function | backend/api/routes/integrations.py | 54-75 |
| delete_setting_endpoint | Function | backend/api/routes/integrations.py | 79-96 |
| _require_pg | Function | backend/api/routes/inventory.py | 52-54 |
| list_users_endpoint | Function | backend/api/routes/inventory.py | 61-67 |
| create_user_endpoint | Function | backend/api/routes/inventory.py | 71-80 |
| get_user_endpoint | Function | backend/api/routes/inventory.py | 84-92 |
| update_user_endpoint | Function | backend/api/routes/inventory.py | 96-105 |
| delete_user_endpoint | Function | backend/api/routes/inventory.py | 109-117 |
| list_assets_endpoint | Function | backend/api/routes/inventory.py | 124-126 |
| create_asset_endpoint | Function | backend/api/routes/inventory.py | 130-138 |
| get_asset_endpoint | Function | backend/api/routes/inventory.py | 142-150 |
| update_asset_endpoint | Function | backend/api/routes/inventory.py | 154-163 |
| delete_asset_endpoint | Function | backend/api/routes/inventory.py | 167-175 |
| list_relationships_endpoint | Function | backend/api/routes/inventory.py | 182-186 |

*... and 266 more members.*

## Execution Flows

- **admin_org_gap_suggest** (criticality: 0.80, depth: 5)
- **assistant_spl_suggest** (criticality: 0.77, depth: 9)
- **run_analysis** (criticality: 0.76, depth: 6)
- **agent_triage_endpoint** (criticality: 0.76, depth: 8)
- **soc_chat** (criticality: 0.75, depth: 5)
- **run_routed_analysis_endpoint** (criticality: 0.74, depth: 7)
- **dashboard_overview** (criticality: 0.74, depth: 8)
- **splunk_ingest** (criticality: 0.74, depth: 3)
- **classify_alert_endpoint** (criticality: 0.73, depth: 6)
- **list_triage_queue** (criticality: 0.73, depth: 6)
- *... and 32 more flows.*

## Dependencies

### Outgoing

- `get` (217 edge(s))
- `len` (111 edge(s))
- `str` (91 edge(s))
- `isinstance` (85 edge(s))
- `info` (85 edge(s))
- `HTTPException` (70 edge(s))
- `warning` (63 edge(s))
- `patch` (46 edge(s))
- `strip` (44 edge(s))
- `Depends` (44 edge(s))
- `format` (44 edge(s))
- `perf_counter` (44 edge(s))
- `append` (35 edge(s))
- `list` (24 edge(s))
- `int` (23 edge(s))

### Incoming

- `patch` (37 edge(s))
- `backend/api/routes/inventory.py` (19 edge(s))
- `len` (16 edge(s))
- `backend/tests/test_alert_classifier_llm.py` (13 edge(s))
- `backend/api/routes/analysis.py` (12 edge(s))
- `backend/tests/test_splunk_json_store.py` (12 edge(s))
- `backend/services/alert/alert_classifier_llm.py` (10 edge(s))
- `backend/services/alert/ingest_request_trace.py` (10 edge(s))
- `get` (10 edge(s))
- `backend/tests/test_ingest_request_trace.py` (10 edge(s))
- `backend/services/soc_analysis/analysis_audit.py` (9 edge(s))
- `backend/tests/test_agent_triage_all_rows.py` (9 edge(s))
- `run` (9 edge(s))
- `AsyncMock` (9 edge(s))
- `backend/api/routes/soc_chat.py` (8 edge(s))
