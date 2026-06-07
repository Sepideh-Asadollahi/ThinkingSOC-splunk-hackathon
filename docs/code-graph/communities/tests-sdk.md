# tests-sdk

## Overview

Community of 51 nodes

- **Size**: 51 nodes
- **Cohesion**: 0.2092
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _ok_response | Function | backend/tests/test_devtools_sdk.py | 30-35 |
| _http_error | Function | backend/tests/test_devtools_sdk.py | 38-43 |
| test_sdk_classify_typed_response | Test | backend/tests/test_devtools_sdk.py | 51-57 |
| test_sdk_auth_error_maps_401 | Test | backend/tests/test_devtools_sdk.py | 60-66 |
| test_sdk_api_error_maps_500 | Test | backend/tests/test_devtools_sdk.py | 69-75 |
| test_sdk_not_found_error_maps_404 | Test | backend/tests/test_devtools_sdk.py | 78-84 |
| test_sdk_retries_on_503_then_succeeds | Test | backend/tests/test_devtools_sdk.py | 98-108 |
| test_sdk_mcp_status | Test | backend/tests/test_devtools_sdk.py | 122-129 |
| test_sdk_mcp_generate_spl | Test | backend/tests/test_devtools_sdk.py | 132-139 |
| test_sdk_mcp_call_tool | Test | backend/tests/test_devtools_sdk.py | 142-149 |
| test_sdk_run_analysis_by_sid | Test | backend/tests/test_devtools_sdk.py | 152-159 |
| test_sdk_search_events | Test | backend/tests/test_devtools_sdk.py | 162-169 |
| test_sdk_get_event | Test | backend/tests/test_devtools_sdk.py | 172-178 |
| test_sdk_dashboard_overview | Test | backend/tests/test_devtools_sdk.py | 181-198 |
| test_sdk_route_analysis | Test | backend/tests/test_devtools_sdk.py | 201-214 |
| test_sdk_run_agent_triage | Test | backend/tests/test_devtools_sdk.py | 217-231 |
| test_sdk_suggest_spl | Test | backend/tests/test_devtools_sdk.py | 234-244 |
| test_sdk_run_analysis | Test | backend/tests/test_devtools_sdk.py | 247-261 |
| test_sdk_get_error_on_get_raises_not_found | Test | backend/tests/test_devtools_sdk.py | 264-270 |
| test_sdk_post_raw_raises_auth_error | Test | backend/tests/test_devtools_sdk.py | 283-289 |
| test_async_sdk_classify_typed_response | Test | backend/tests/test_devtools_sdk.py | 311-317 |
| test_async_sdk_auth_error | Test | backend/tests/test_devtools_sdk.py | 321-329 |
| test_async_sdk_mcp_status | Test | backend/tests/test_devtools_sdk.py | 344-350 |
| test_async_sdk_mcp_generate_spl | Test | backend/tests/test_devtools_sdk.py | 354-360 |
| test_async_sdk_mcp_call_tool | Test | backend/tests/test_devtools_sdk.py | 364-370 |
| test_async_sdk_dashboard_overview | Test | backend/tests/test_devtools_sdk.py | 374-390 |
| test_async_sdk_search_events | Test | backend/tests/test_devtools_sdk.py | 394-400 |
| test_sdk_run_observability | Test | backend/tests/test_devtools_sdk.py | 660-676 |
| test_sdk_run_observability_by_sid | Test | backend/tests/test_devtools_sdk.py | 679-685 |
| test_sdk_soc_chat | Test | backend/tests/test_devtools_sdk.py | 688-694 |
| test_sdk_soc_chat_status | Test | backend/tests/test_devtools_sdk.py | 697-704 |
| test_sdk_investigation_timeline | Test | backend/tests/test_devtools_sdk.py | 707-714 |
| test_sdk_analyst_actions | Test | backend/tests/test_devtools_sdk.py | 717-723 |
| test_sdk_add_analyst_action | Test | backend/tests/test_devtools_sdk.py | 726-732 |
| test_sdk_triage_queue | Test | backend/tests/test_devtools_sdk.py | 735-741 |
| test_sdk_health | Test | backend/tests/test_devtools_sdk.py | 744-750 |
| test_async_sdk_route_analysis | Test | backend/tests/test_devtools_sdk.py | 759-770 |
| test_async_sdk_run_agent_triage | Test | backend/tests/test_devtools_sdk.py | 774-786 |
| test_async_sdk_suggest_spl | Test | backend/tests/test_devtools_sdk.py | 790-799 |
| test_async_sdk_run_analysis | Test | backend/tests/test_devtools_sdk.py | 803-816 |
| test_async_sdk_run_analysis_by_sid | Test | backend/tests/test_devtools_sdk.py | 820-827 |
| test_async_sdk_get_event | Test | backend/tests/test_devtools_sdk.py | 831-837 |
| test_async_sdk_run_observability_by_sid | Test | backend/tests/test_devtools_sdk.py | 841-847 |
| test_async_sdk_soc_chat_status | Test | backend/tests/test_devtools_sdk.py | 851-857 |
| test_async_sdk_analyst_actions | Test | backend/tests/test_devtools_sdk.py | 861-867 |
| test_async_sdk_add_analyst_action | Test | backend/tests/test_devtools_sdk.py | 871-877 |
| test_async_sdk_run_observability | Test | backend/tests/test_devtools_sdk.py | 881-896 |
| test_async_sdk_soc_chat | Test | backend/tests/test_devtools_sdk.py | 900-906 |
| test_async_sdk_triage_queue | Test | backend/tests/test_devtools_sdk.py | 910-916 |
| test_async_sdk_investigation_timeline | Test | backend/tests/test_devtools_sdk.py | 920-926 |

*... and 1 more members.*

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `patch` (49 edge(s))
- `backend/devtools/__init__.py::TsocSdkClient` (27 edge(s))
- `backend/devtools/__init__.py::AsyncTsocSdkClient` (22 edge(s))
- `classify_alert` (7 edge(s))
- `raises` (6 edge(s))
- `MagicMock` (3 edge(s))
- `add_analyst_action` (3 edge(s))
- `backend/devtools/__init__.py::TsocAuthError` (3 edge(s))
- `get_event` (3 edge(s))
- `len` (3 edge(s))
- `analyst_actions` (2 edge(s))
- `dashboard_overview` (2 edge(s))
- `health` (2 edge(s))
- `investigation_timeline` (2 edge(s))
- `mcp_call_tool` (2 edge(s))

### Incoming

- `backend/tests/test_devtools_sdk.py` (51 edge(s))
- `patch` (49 edge(s))
- `backend/devtools/__init__.py::TsocSdkClient` (27 edge(s))
- `backend/devtools/__init__.py::AsyncTsocSdkClient` (22 edge(s))
- `classify_alert` (7 edge(s))
- `raises` (6 edge(s))
- `add_analyst_action` (3 edge(s))
- `get_event` (3 edge(s))
- `len` (3 edge(s))
- `analyst_actions` (2 edge(s))
- `MagicMock` (2 edge(s))
- `dashboard_overview` (2 edge(s))
- `health` (2 edge(s))
- `investigation_timeline` (2 edge(s))
- `mcp_call_tool` (2 edge(s))
