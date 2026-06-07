# tests-mcp

## Overview

Community of 168 nodes

- **Size**: 168 nodes
- **Cohesion**: 0.2836
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| Settings | Class | backend/config.py | 12-199 |
| mcp_configured | Function | backend/config.py | 202-209 |
| splunk_mcp_url_for | Function | backend/config.py | 212-218 |
| McpQueryEvidence | Class | backend/models/mcp.py | 15-21 |
| McpSaiaAnswer | Class | backend/models/mcp.py | 24-28 |
| McpHunterEvidence | Class | backend/models/mcp.py | 31-37 |
| McpJudgeEvidence | Class | backend/models/mcp.py | 40-46 |
| McpAlertContext | Class | backend/models/mcp.py | 49-61 |
| McpStatusResponse | Class | backend/models/mcp.py | 64-71 |
| SplSaiaAnalysis | Class | backend/models/analysis.py | 81-103 |
| AlertClassificationResult | Class | backend/models/agentic_ops.py | 15-23 |
| test_mcp_status_not_configured | Test | backend/tests/test_mcp_status.py | 14-20 |
| _override | Function | backend/tests/test_ingest_background.py | 16-21 |
| test_run_post_ingest_calls_triage | Test | backend/tests/test_ingest_background.py | 38-53 |
| _run | Function | backend/tests/test_ingest_background.py | 39-51 |
| _rpc_result | Function | backend/tests/mcp_rpc_mock.py | 8-9 |
| build_mcp_rpc_mock | Function | backend/tests/mcp_rpc_mock.py | 12-34 |
| _rpc | Function | backend/tests/mcp_rpc_mock.py | 21-32 |
| test_litellm_chat_completion_accepts_system_and_user_messages | Test | backend/tests/test_llm.py | 123-153 |
| _run | Function | backend/tests/test_llm.py | 141-145 |
| _load | Function | backend/tests/test_spl_saia_analysis.py | 21-23 |
| test_analyze_investigation_spl_with_saia_optimize_explain | Test | backend/tests/test_spl_saia_analysis.py | 27-64 |
| _load | Function | backend/tests/test_mcp_client.py | 19-21 |
| _mcp_settings | Function | backend/tests/test_mcp_client.py | 24-30 |
| test_resolve_tool_name_aliases | Test | backend/tests/test_mcp_client.py | 34-37 |
| test_mcp_client_initialize_and_list_tools | Test | backend/tests/test_mcp_client.py | 41-53 |
| test_mcp_call_tool_saia | Test | backend/tests/test_mcp_client.py | 57-73 |
| test_integrations_uses_admin_token_when_configured | Test | backend/tests/test_auth_guards.py | 61-90 |
| test_rate_limit_enforced_on_sensitive_route | Test | backend/tests/test_auth_guards.py | 93-121 |
| test_suggest_spl_rule_based_when_llm_disabled | Test | backend/tests/test_spl_mcp_review.py | 58-73 |
| test_serialize_full_no_truncation | Test | backend/tests/test_full_trace_log.py | 8-12 |
| test_agent_triage_includes_mcp_fields_when_mocked | Test | backend/tests/test_agents_mcp.py | 37-124 |
| _load | Function | backend/tests/test_spl_saia_postprocess.py | 19-21 |
| test_saia_pipeline_generate_optimize_explain | Test | backend/tests/test_spl_saia_postprocess.py | 25-70 |
| _make_transport_v2 | Function | backend/tests/test_splunk_client.py | 25-42 |
| settings_v2 | Function | backend/tests/test_splunk_client.py | 46-52 |
| test_login_get_job_fetch_results_v2 | Test | backend/tests/test_splunk_client.py | 56-75 |
| test_login_requires_credentials | Test | backend/tests/test_splunk_client.py | 79-88 |
| _llm_response | Function | backend/tests/test_alert_classifier_llm.py | 17-27 |
| test_classify_alert_fallback_is_manual_review | Test | backend/tests/test_alert_classifier_llm.py | 30-34 |
| test_build_payload_includes_all_rows_and_mcp | Test | backend/tests/test_alert_classifier_llm.py | 37-47 |
| test_classify_hybrid_uses_llm_with_full_payload | Test | backend/tests/test_alert_classifier_llm.py | 50-77 |
| _run | Function | backend/tests/test_alert_classifier_llm.py | 115-127 |
| test_classify_hybrid_falls_back_when_llm_disabled | Test | backend/tests/test_alert_classifier_llm.py | 80-86 |
| test_classify_hybrid_rejects_dual_from_llm | Test | backend/tests/test_alert_classifier_llm.py | 89-111 |
| test_classify_hybrid_falls_back_on_llm_error | Test | backend/tests/test_alert_classifier_llm.py | 114-129 |
| _mock_pool_with_conn | Function | backend/tests/test_splunk_json_store.py | 34-41 |
| test_splunk_store_not_configured_without_postgres_dsn | Test | backend/tests/test_splunk_json_store.py | 44-46 |
| test_splunk_store_configured_when_dsn_set | Test | backend/tests/test_splunk_json_store.py | 49-51 |
| test_submit_event_skips_when_store_not_configured | Test | backend/tests/test_splunk_json_store.py | 72-75 |

*... and 118 more members.*

## Execution Flows

- **execute_investigation_spl** (criticality: 0.84, depth: 5)
- **assistant_spl_suggest** (criticality: 0.78, depth: 9)
- **assemble_from_langgraph** (criticality: 0.77, depth: 8)
- **splunk_ingest** (criticality: 0.76, depth: 9)
- **agent_triage_endpoint** (criticality: 0.75, depth: 8)
- **run_routed_analysis_endpoint** (criticality: 0.74, depth: 7)
- **dashboard_overview** (criticality: 0.74, depth: 8)
- **work** (criticality: 0.74, depth: 6)
- **classify_alert_endpoint** (criticality: 0.73, depth: 6)
- **work** (criticality: 0.73, depth: 5)
- *... and 15 more flows.*

## Dependencies

### Outgoing

- `get` (68 edge(s))
- `isinstance` (53 edge(s))
- `append` (49 edge(s))
- `str` (46 edge(s))
- `format` (42 edge(s))
- `strip` (36 edge(s))
- `len` (23 edge(s))
- `getattr` (17 edge(s))
- `info` (16 edge(s))
- `call_tool` (16 edge(s))
- `bool` (15 edge(s))
- `patch` (15 edge(s))
- `warning` (11 edge(s))
- `ensure_ready` (10 edge(s))
- `resolve_tool_name` (9 edge(s))

### Incoming

- `get` (15 edge(s))
- `backend/services/llm/full_trace_log.py` (14 edge(s))
- `backend/splunk/mcp/hunter_judge_context.py` (14 edge(s))
- `backend/tests/test_splunk_json_store.py` (12 edge(s))
- `backend/tests/test_alert_classifier_llm.py` (11 edge(s))
- `len` (11 edge(s))
- `backend/services/alert/alert_classifier_llm.py` (10 edge(s))
- `patch` (9 edge(s))
- `backend/tests/test_splunk_live_mcp_saia.py` (8 edge(s))
- `run` (7 edge(s))
- `backend/models/mcp.py` (6 edge(s))
- `backend/tests/test_hunter_judge_mcp.py` (6 edge(s))
- `object` (6 edge(s))
- `lower` (6 edge(s))
- `skip` (6 edge(s))
