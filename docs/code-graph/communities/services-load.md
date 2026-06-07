# services-load

## Overview

Community of 64 nodes

- **Size**: 64 nodes
- **Cohesion**: 0.2159
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| FrameworkMappingItem | Class | backend/models/analysis.py | 12-17 |
| JudgeVerdict | Class | backend/models/analysis.py | 20-25 |
| HunterSection | Class | backend/models/analysis.py | 28-32 |
| RootCauseSplValidation | Class | backend/models/analysis.py | 35-40 |
| RootCauseSpl | Class | backend/models/analysis.py | 43-51 |
| SocAnalysisResult | Class | backend/models/analysis.py | 54-70 |
| AdminOrgGapSuggestRequest | Class | backend/models/admin_org.py | 10-21 |
| AdminOrgGapSuggestResponse | Class | backend/models/admin_org.py | 24-30 |
| RootCauseHypothesis | Class | backend/models/observability.py | 28-32 |
| DiagnoserSection | Class | backend/models/observability.py | 35-37 |
| ResponderSection | Class | backend/models/observability.py | 40-42 |
| OpsJudgeVerdict | Class | backend/models/observability.py | 45-51 |
| root_cause_spl_user_message | Function | backend/services/soc_analysis_root_cause_spl.py | 48-69 |
| _has_forbidden_command | Function | backend/services/soc_analysis_root_cause_spl.py | 72-78 |
| sanitize_root_cause_spl_output | Function | backend/services/soc_analysis_root_cause_spl.py | 81-119 |
| _esc_spl_lit | Function | backend/services/soc_analysis_root_cause_spl.py | 122-124 |
| build_rule_based_root_cause_spl | Function | backend/services/soc_analysis_root_cause_spl.py | 127-204 |
| validate_root_cause_spl | Function | backend/services/soc_analysis_root_cause_spl.py | 207-246 |
| build_canonical_static_context | Function | backend/services/soc_analysis_canonical.py | 14-43 |
| load_prompt_file | Function | backend/services/soc_analysis_prompts.py | 22-23 |
| load_defender_system_prompt | Function | backend/services/soc_analysis_prompts.py | 26-27 |
| load_hunter_system_prompt | Function | backend/services/soc_analysis_prompts.py | 30-31 |
| load_judge_system_prompt | Function | backend/services/soc_analysis_prompts.py | 34-35 |
| load_investigation_questions_system_prompt | Function | backend/services/soc_analysis_prompts.py | 38-39 |
| load_framework_mapping_system_prompt | Function | backend/services/soc_analysis_prompts.py | 41-42 |
| load_admin_org_gap_system_prompt | Function | backend/services/soc_analysis_prompts.py | 45-46 |
| load_root_cause_spl_system_prompt | Function | backend/services/soc_analysis_prompts.py | 49-50 |
| parse_llm_json_response | Function | backend/services/soc_analysis_json.py | 12-17 |
| _load_prompt_file | Function | backend/services/observability_prompts.py | 14-15 |
| load_observability_diagnoser_system_prompt | Function | backend/services/observability_prompts.py | 18-19 |
| load_observability_responder_system_prompt | Function | backend/services/observability_prompts.py | 22-23 |
| load_observability_ops_judge_system_prompt | Function | backend/services/observability_prompts.py | 26-27 |
| _norm_verdict | Function | backend/services/soc_verdict.py | 8-12 |
| verdict_implies_false_positive | Function | backend/services/soc_verdict.py | 31-38 |
| sanitize_investigation_questions | Function | backend/services/soc_verdict.py | 41-56 |
| investigation_questions_for_verdict | Function | backend/services/soc_verdict.py | 59-63 |
| _fallback_response | Function | backend/services/admin_org_gap.py | 18-41 |
| suggest_admin_org_gap | Function | backend/services/admin_org_gap.py | 44-117 |
| LiteLLMNotConfiguredError | Class | backend/services/litellm_service.py | 13-14 |
| _normalize_messages | Function | backend/services/litellm_service.py | 17-27 |
| litellm_chat_completion | Function | backend/services/litellm_service.py | 30-104 |
| _review_user_message | Function | backend/services/spl_mcp_review.py | 21-54 |
| review_spl_from_mcp_with_llm | Function | backend/services/spl_mcp_review.py | 57-117 |
| _fake_spl | Function | backend/tests/test_agents_mcp.py | 94-101 |
| test_suggest_admin_org_gap_fallback_no_identity | Test | backend/tests/test_admin_org_gap.py | 15-26 |
| test_suggest_admin_org_gap_fallback_with_asset | Test | backend/tests/test_admin_org_gap.py | 30-37 |
| build_fallback_soc_result | Function | backend/services/soc_analysis/fallback_result.py | 22-89 |
| assemble_from_langgraph | Function | backend/services/soc_analysis/assembly.py | 22-108 |
| build_ops_judge | Function | backend/services/observability_analysis/judge.py | 8-46 |
| _context_json | Function | backend/services/observability_analysis/llm.py | 19-20 |

*... and 14 more members.*

## Execution Flows

- **admin_org_gap_suggest** (criticality: 0.80, depth: 3)
- **splunk_ingest** (criticality: 0.75, depth: 7)
- **agent_triage_endpoint** (criticality: 0.74, depth: 6)
- **mcp_spl_generate_endpoint** (criticality: 0.73, depth: 4)
- **assistant_spl_suggest** (criticality: 0.73, depth: 5)
- **run_routed_analysis_endpoint** (criticality: 0.73, depth: 4)
- **work** (criticality: 0.72, depth: 5)
- **classify_alert_endpoint** (criticality: 0.71, depth: 3)
- **build_diagnoser_llm** (criticality: 0.68, depth: 3)
- **build_responder_llm** (criticality: 0.68, depth: 3)
- *... and 9 more flows.*

## Dependencies

### Outgoing

- `get` (87 edge(s))
- `str` (49 edge(s))
- `format` (29 edge(s))
- `strip` (28 edge(s))
- `append` (27 edge(s))
- `isinstance` (17 edge(s))
- `BaseModel` (12 edge(s))
- `getattr` (11 edge(s))
- `dumps` (8 edge(s))
- `len` (7 edge(s))
- `info` (7 edge(s))
- `llm_json_response` (6 edge(s))
- `replace` (5 edge(s))
- `warning` (4 edge(s))
- `lower` (4 edge(s))

### Incoming

- `backend/services/observability_analysis/llm.py` (8 edge(s))
- `backend/services/soc_analysis_prompts.py` (8 edge(s))
- `backend/models/analysis.py` (6 edge(s))
- `backend/services/soc_analysis_root_cause_spl.py` (6 edge(s))
- `backend/services/soc_analysis_graph/nodes_llm.py` (5 edge(s))
- `backend/services/splunk_ai_assistant.py::suggest_spl_for_alert` (5 edge(s))
- `backend/models/observability.py` (4 edge(s))
- `backend/services/observability_prompts.py` (4 edge(s))
- `backend/services/soc_verdict.py` (4 edge(s))
- `backend/services/litellm_service.py` (3 edge(s))
- `backend/services/observability_analysis/diagnoser.py` (3 edge(s))
- `backend/services/soc_analysis_graph/nodes_canonical.py::work` (3 edge(s))
- `backend/models/admin_org.py` (2 edge(s))
- `backend/splunk/mcp/spl_assistant.py::_call_saia_generate` (2 edge(s))
- `backend/services/admin_org_gap.py` (2 edge(s))
