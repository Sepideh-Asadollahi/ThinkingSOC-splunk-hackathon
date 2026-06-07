# soc-analysis-gap

## Overview

Community of 55 nodes

- **Size**: 55 nodes
- **Cohesion**: 0.2649
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| AdminOrgGapSuggestRequest | Class | backend/models/admin_org.py | 10-23 |
| AdminOrgGapSuggestResponse | Class | backend/models/admin_org.py | 26-32 |
| RootCauseHypothesis | Class | backend/models/observability.py | 29-33 |
| DiagnoserSection | Class | backend/models/observability.py | 36-38 |
| ResponderSection | Class | backend/models/observability.py | 41-43 |
| OpsJudgeVerdict | Class | backend/models/observability.py | 46-52 |
| test_parse_plain_json | Test | backend/tests/test_soc_analysis_json.py | 16-18 |
| test_parse_fenced_json | Test | backend/tests/test_soc_analysis_json.py | 21-28 |
| test_parse_prose_then_json_object | Test | backend/tests/test_soc_analysis_json.py | 31-40 |
| test_parse_empty_raises | Test | backend/tests/test_soc_analysis_json.py | 43-45 |
| test_salvage_hunter_spl_lines | Test | backend/tests/test_soc_analysis_json.py | 48-57 |
| test_salvage_investigation_questions_from_reasoning | Test | backend/tests/test_soc_analysis_json.py | 60-68 |
| test_parse_recover_bare_hunter_spl | Test | backend/tests/test_soc_analysis_json.py | 71-78 |
| test_suggest_admin_org_gap_fallback_no_identity | Test | backend/tests/test_admin_org_gap.py | 24-35 |
| test_suggest_admin_org_gap_fallback_with_asset | Test | backend/tests/test_admin_org_gap.py | 39-46 |
| test_rule_based_osk_gap_even_when_asset_linked | Test | backend/tests/test_admin_org_gap.py | 50-71 |
| test_suggest_admin_org_gap_fallback_osk_with_asset | Test | backend/tests/test_admin_org_gap.py | 75-88 |
| test_build_admin_org_gap_request_from_soc_result | Test | backend/tests/test_admin_org_gap.py | 103-144 |
| test_persist_soc_analysis_includes_admin_org_gap | Test | backend/tests/test_admin_org_gap.py | 279-310 |
| load_admin_org_gap_system_prompt | Function | backend/services/soc_analysis/soc_analysis_prompts.py | 45-46 |
| _balanced_json_objects | Function | backend/services/soc_analysis/soc_analysis_json.py | 13-47 |
| _try_load_json | Function | backend/services/soc_analysis/soc_analysis_json.py | 50-55 |
| _strip_wrapped_quotes | Function | backend/services/soc_analysis/soc_analysis_json.py | 58-64 |
| _is_spl_line | Function | backend/services/soc_analysis/soc_analysis_json.py | 67-71 |
| _extract_spl_lines | Function | backend/services/soc_analysis/soc_analysis_json.py | 74-88 |
| salvage_hunter_json_from_text | Function | backend/services/soc_analysis/soc_analysis_json.py | 91-144 |
| salvage_investigation_questions_from_text | Function | backend/services/soc_analysis/soc_analysis_json.py | 147-163 |
| parse_llm_json_response | Function | backend/services/soc_analysis/soc_analysis_json.py | 166-200 |
| _truncate | Function | backend/services/soc_analysis/admin_org_gap.py | 54-60 |
| _alert_text_blob | Function | backend/services/soc_analysis/admin_org_gap.py | 63-80 |
| _host_label | Function | backend/services/soc_analysis/admin_org_gap.py | 83-92 |
| _detect_process_org_gap | Function | backend/services/soc_analysis/admin_org_gap.py | 95-111 |
| _weak_identity | Function | backend/services/soc_analysis/admin_org_gap.py | 114-115 |
| rule_based_admin_org_gap | Function | backend/services/soc_analysis/admin_org_gap.py | 118-161 |
| build_admin_org_gap_request | Function | backend/services/soc_analysis/admin_org_gap.py | 164-181 |
| attach_admin_org_gap | Function | backend/services/soc_analysis/admin_org_gap.py | 184-193 |
| _fallback_response | Function | backend/services/soc_analysis/admin_org_gap.py | 196-207 |
| suggest_admin_org_gap | Function | backend/services/soc_analysis/admin_org_gap.py | 210-287 |
| build_ops_judge | Function | backend/services/observability_analysis/judge.py | 8-46 |
| _load_prompt_file | Function | backend/services/observability_analysis/observability_prompts.py | 14-15 |
| load_observability_diagnoser_system_prompt | Function | backend/services/observability_analysis/observability_prompts.py | 18-19 |
| load_observability_responder_system_prompt | Function | backend/services/observability_analysis/observability_prompts.py | 22-23 |
| load_observability_ops_judge_system_prompt | Function | backend/services/observability_analysis/observability_prompts.py | 26-27 |
| _context_json | Function | backend/services/observability_analysis/llm.py | 19-20 |
| _llm_json_response | Function | backend/services/observability_analysis/llm.py | 23-33 |
| _to_diagnoser | Function | backend/services/observability_analysis/llm.py | 36-58 |
| _to_responder | Function | backend/services/observability_analysis/llm.py | 61-70 |
| _to_ops_judge | Function | backend/services/observability_analysis/llm.py | 73-82 |
| build_diagnoser_llm | Function | backend/services/observability_analysis/llm.py | 85-89 |
| build_responder_llm | Function | backend/services/observability_analysis/llm.py | 92-96 |

*... and 5 more members.*

## Execution Flows

- **admin_org_gap_suggest** (criticality: 0.80, depth: 5)
- **assistant_spl_suggest** (criticality: 0.78, depth: 9)
- **assemble_from_langgraph** (criticality: 0.77, depth: 8)
- **splunk_ingest** (criticality: 0.76, depth: 9)
- **run_analysis** (criticality: 0.76, depth: 6)
- **agent_triage_endpoint** (criticality: 0.75, depth: 8)
- **review_spl_from_mcp_with_llm** (criticality: 0.73, depth: 5)
- **build_responder_llm** (criticality: 0.72, depth: 5)
- **build_ops_judge_llm** (criticality: 0.72, depth: 5)
- **build_diagnoser_llm** (criticality: 0.72, depth: 5)
- *... and 2 more flows.*

## Dependencies

### Outgoing

- `get` (30 edge(s))
- `str` (27 edge(s))
- `strip` (25 edge(s))
- `format` (19 edge(s))
- `append` (18 edge(s))
- `lower` (10 edge(s))
- `isinstance` (8 edge(s))
- `BaseModel` (6 edge(s))
- `len` (6 edge(s))
- `search` (4 edge(s))
- `split` (3 edge(s))
- `loads` (3 edge(s))
- `dumps` (2 edge(s))
- `backend/services/llm/litellm_service.py::litellm_chat_completion` (2 edge(s))
- `max` (2 edge(s))

### Incoming

- `backend/services/soc_analysis/admin_org_gap.py` (10 edge(s))
- `backend/services/observability_analysis/llm.py` (8 edge(s))
- `backend/services/soc_analysis/soc_analysis_json.py` (8 edge(s))
- `backend/tests/test_soc_analysis_json.py` (7 edge(s))
- `backend/tests/test_admin_org_gap.py` (6 edge(s))
- `backend/models/observability.py` (4 edge(s))
- `backend/services/observability_analysis/observability_prompts.py` (4 edge(s))
- `backend/services/observability_analysis/diagnoser.py` (3 edge(s))
- `backend/services/soc_analysis_graph/llm.py::llm_json_response` (3 edge(s))
- `lower` (3 edge(s))
- `backend/models/admin_org.py` (2 edge(s))
- `backend/models/analysis.py::AnalysisRunRequest` (2 edge(s))
- `EnrichmentResult` (2 edge(s))
- `SocAnalysisResult` (2 edge(s))
- `HunterSection` (2 edge(s))
