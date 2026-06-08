# tests-spl

## Overview

Community of 270 nodes

- **Size**: 270 nodes
- **Cohesion**: 0.2800
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| mcp_status_endpoint | Function | backend/api/routes/mcp.py | 28-32 |
| mcp_tool_call_endpoint | Function | backend/api/routes/mcp.py | 89-109 |
| mcp_configured | Function | backend/config.py | 221-228 |
| splunk_mcp_url_for | Function | backend/config.py | 231-237 |
| investigation_questions_max | Function | backend/config.py | 261-263 |
| RootCauseSplValidation | Class | backend/models/analysis.py | 46-51 |
| RootCauseSpl | Class | backend/models/analysis.py | 54-69 |
| SplSearchResult | Class | backend/models/analysis.py | 72-78 |
| SplSaiaAnalysis | Class | backend/models/analysis.py | 81-103 |
| InvestigationQuestionItem | Class | backend/models/analysis.py | 106-131 |
| DashboardIntegrations | Class | backend/models/dashboard.py | 47-51 |
| McpQueryEvidence | Class | backend/models/mcp.py | 15-21 |
| McpSaiaAnswer | Class | backend/models/mcp.py | 24-28 |
| McpHunterEvidence | Class | backend/models/mcp.py | 31-37 |
| McpJudgeEvidence | Class | backend/models/mcp.py | 40-46 |
| McpStatusResponse | Class | backend/models/mcp.py | 64-71 |
| McpToolCallResponse | Class | backend/models/mcp.py | 79-81 |
| _merge_result_row | Function | backend/services/alert/alert_fields.py | 8-28 |
| build_alert_fields_for_llm | Function | backend/services/alert/alert_fields.py | 31-61 |
| merge_alert_field_sample | Function | backend/services/investigation/investigation_question_context.py | 68-87 |
| _fields_from_orig_search | Function | backend/services/investigation/investigation_question_context.py | 90-97 |
| _truncate_val | Function | backend/services/investigation/investigation_question_context.py | 100-104 |
| primary_alert_fields | Function | backend/services/investigation/investigation_question_context.py | 107-154 |
| format_alert_fields_block | Function | backend/services/investigation/investigation_question_context.py | 157-169 |
| postprocess_investigation_question_strings | Function | backend/services/investigation/investigation_question_context.py | 325-349 |
| _item_from_question_and_spl | Function | backend/services/investigation/investigation_questions_spl.py | 43-73 |
| sanitize_investigation_question_items | Function | backend/services/investigation/investigation_questions_spl.py | 76-126 |
| validate_investigation_question_items | Function | backend/services/investigation/investigation_questions_spl.py | 129-179 |
| investigation_questions_for_verdict | Function | backend/services/investigation/investigation_questions_spl.py | 182-203 |
| generate_investigation_spl_via_llm | Function | backend/services/investigation/investigation_questions_spl.py | 206-259 |
| fill_investigation_spl | Function | backend/services/investigation/investigation_questions_spl.py | 262-390 |
| run_investigation_item_execute_refine_loop | Function | backend/services/investigation/investigation_questions_spl.py | 393-544 |
| finalize_investigation_questions_for_verdict | Function | backend/services/investigation/investigation_questions_spl.py | 547-647 |
| needs_spl_execution_refine | Function | backend/services/investigation/investigation_spl_execute.py | 34-40 |
| _readable_cell | Function | backend/services/investigation/investigation_spl_execute.py | 43-53 |
| _readable_rows | Function | backend/services/investigation/investigation_spl_execute.py | 56-62 |
| execute_investigation_spl | Function | backend/services/investigation/investigation_spl_execute.py | 65-106 |
| execute_investigation_item | Function | backend/services/investigation/investigation_spl_execute.py | 109-145 |
| _run_one | Function | backend/services/investigation/investigation_spl_execute.py | 148-203 |
| spl_validation_is_error | Function | backend/services/investigation/spl_mcp_review.py | 23-27 |
| _spl_error_refine_max_attempts | Function | backend/services/investigation/spl_mcp_review.py | 30-31 |
| _spl_error_refine_enabled | Function | backend/services/investigation/spl_mcp_review.py | 34-35 |
| _review_user_message | Function | backend/services/investigation/spl_mcp_review.py | 38-86 |
| review_spl_from_mcp_with_llm | Function | backend/services/investigation/spl_mcp_review.py | 89-175 |
| _execution_feedback_message | Function | backend/services/investigation/spl_mcp_review.py | 178-185 |
| _spl_error_refine_user_message | Function | backend/services/investigation/spl_mcp_review.py | 188-259 |
| _execution_refine_user_message | Function | backend/services/investigation/spl_mcp_review.py | 262-314 |
| _splunk_catalog_block | Function | backend/services/investigation/spl_mcp_review.py | 317-354 |
| refine_spl_with_llm_on_error | Function | backend/services/investigation/spl_mcp_review.py | 357-441 |
| refine_root_cause_spl_until_valid | Function | backend/services/investigation/spl_mcp_review.py | 444-503 |

*... and 220 more members.*

## Execution Flows

- **execute_investigation_spl** (criticality: 0.84, depth: 5)
- **admin_org_gap_suggest** (criticality: 0.80, depth: 5)
- **assistant_spl_suggest** (criticality: 0.77, depth: 9)
- **assemble_from_langgraph** (criticality: 0.77, depth: 8)
- **run_analysis** (criticality: 0.76, depth: 6)
- **agent_triage_endpoint** (criticality: 0.76, depth: 8)
- **run_routed_analysis_endpoint** (criticality: 0.74, depth: 7)
- **dashboard_overview** (criticality: 0.74, depth: 8)
- **work** (criticality: 0.74, depth: 6)
- **review_spl_from_mcp_with_llm** (criticality: 0.73, depth: 5)
- *... and 20 more flows.*

## Dependencies

### Outgoing

- `get` (151 edge(s))
- `append` (132 edge(s))
- `strip` (108 edge(s))
- `isinstance` (105 edge(s))
- `format` (96 edge(s))
- `str` (89 edge(s))
- `len` (66 edge(s))
- `getattr` (35 edge(s))
- `info` (33 edge(s))
- `lower` (29 edge(s))
- `join` (27 edge(s))
- `list` (24 edge(s))
- `bool` (22 edge(s))
- `model_copy` (22 edge(s))
- `patch` (22 edge(s))

### Incoming

- `patch` (22 edge(s))
- `backend/services/soc_analysis/soc_analysis_root_cause_spl.py` (15 edge(s))
- `len` (15 edge(s))
- `backend/services/llm/full_trace_log.py` (14 edge(s))
- `backend/splunk/mcp/hunter_judge_context.py` (14 edge(s))
- `backend/services/investigation/spl_mcp_review.py` (12 edge(s))
- `model_copy` (12 edge(s))
- `backend/services/investigation/spl_predict_pipeline.py` (10 edge(s))
- `lower` (10 edge(s))
- `get` (10 edge(s))
- `backend/tests/test_splunk_live_mcp_saia.py` (10 edge(s))
- `backend/services/investigation/investigation_questions_spl.py` (8 edge(s))
- `backend/splunk/mcp/saia/parse.py` (8 edge(s))
- `backend/services/soc_analysis/soc_analysis_prompts.py` (7 edge(s))
- `backend/services/soc_rag/compact_alert.py` (7 edge(s))
