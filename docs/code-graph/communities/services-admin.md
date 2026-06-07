# services-admin

## Overview

Community of 41 nodes

- **Size**: 41 nodes
- **Cohesion**: 0.2238
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| AdminOrgGapSuggestRequest | Class | backend/models/admin_org.py | 10-21 |
| AdminOrgGapSuggestResponse | Class | backend/models/admin_org.py | 24-30 |
| RootCauseHypothesis | Class | backend/models/observability.py | 29-33 |
| DiagnoserSection | Class | backend/models/observability.py | 36-38 |
| ResponderSection | Class | backend/models/observability.py | 41-43 |
| OpsJudgeVerdict | Class | backend/models/observability.py | 46-52 |
| load_admin_org_gap_system_prompt | Function | backend/services/soc_analysis_prompts.py | 45-46 |
| parse_llm_json_response | Function | backend/services/soc_analysis_json.py | 12-17 |
| _load_prompt_file | Function | backend/services/observability_prompts.py | 14-15 |
| load_observability_diagnoser_system_prompt | Function | backend/services/observability_prompts.py | 18-19 |
| load_observability_responder_system_prompt | Function | backend/services/observability_prompts.py | 22-23 |
| load_observability_ops_judge_system_prompt | Function | backend/services/observability_prompts.py | 26-27 |
| _truncate | Function | backend/services/admin_org_gap.py | 22-28 |
| build_admin_org_gap_request | Function | backend/services/admin_org_gap.py | 31-46 |
| attach_admin_org_gap | Function | backend/services/admin_org_gap.py | 49-58 |
| _fallback_response | Function | backend/services/admin_org_gap.py | 61-84 |
| suggest_admin_org_gap | Function | backend/services/admin_org_gap.py | 87-160 |
| LiteLLMNotConfiguredError | Class | backend/services/litellm_service.py | 13-14 |
| _normalize_messages | Function | backend/services/litellm_service.py | 17-27 |
| litellm_chat_completion | Function | backend/services/litellm_service.py | 30-104 |
| test_suggest_admin_org_gap_fallback_no_identity | Test | backend/tests/test_admin_org_gap.py | 19-30 |
| test_suggest_admin_org_gap_fallback_with_asset | Test | backend/tests/test_admin_org_gap.py | 34-41 |
| test_build_admin_org_gap_request_from_soc_result | Test | backend/tests/test_admin_org_gap.py | 56-97 |
| test_persist_soc_analysis_includes_admin_org_gap | Test | backend/tests/test_admin_org_gap.py | 154-188 |
| build_ops_judge | Function | backend/services/observability_analysis/judge.py | 8-46 |
| _context_json | Function | backend/services/observability_analysis/llm.py | 19-20 |
| _llm_json_response | Function | backend/services/observability_analysis/llm.py | 23-33 |
| _to_diagnoser | Function | backend/services/observability_analysis/llm.py | 36-58 |
| _to_responder | Function | backend/services/observability_analysis/llm.py | 61-70 |
| _to_ops_judge | Function | backend/services/observability_analysis/llm.py | 73-82 |
| build_diagnoser_llm | Function | backend/services/observability_analysis/llm.py | 85-89 |
| build_responder_llm | Function | backend/services/observability_analysis/llm.py | 92-96 |
| build_ops_judge_llm | Function | backend/services/observability_analysis/llm.py | 99-103 |
| _to_float | Function | backend/services/observability_analysis/diagnoser.py | 10-16 |
| _build_searches | Function | backend/services/observability_analysis/diagnoser.py | 19-27 |
| build_diagnoser | Function | backend/services/observability_analysis/diagnoser.py | 30-101 |
| build_responder | Function | backend/services/observability_analysis/responder.py | 8-27 |
| _last_user_message | Function | backend/services/ragflow/chat.py | 25-29 |
| _build_context_block | Function | backend/services/ragflow/chat.py | 32-45 |
| run_soc_chat | Function | backend/services/ragflow/chat.py | 48-155 |
| llm_json_response | Function | backend/services/soc_analysis_graph/llm.py | 12-29 |

## Execution Flows

- **admin_org_gap_suggest** (criticality: 0.82, depth: 3)
- **splunk_ingest** (criticality: 0.74, depth: 7)
- **run_analysis** (criticality: 0.74, depth: 5)
- **agent_triage_endpoint** (criticality: 0.73, depth: 6)
- **assistant_spl_suggest** (criticality: 0.73, depth: 5)
- **run_routed_analysis_endpoint** (criticality: 0.72, depth: 4)
- **classify_alert_endpoint** (criticality: 0.71, depth: 3)
- **build_diagnoser_llm** (criticality: 0.68, depth: 3)
- **build_responder_llm** (criticality: 0.68, depth: 3)
- **build_ops_judge_llm** (criticality: 0.68, depth: 3)
- *... and 5 more flows.*

## Dependencies

### Outgoing

- `get` (35 edge(s))
- `str` (26 edge(s))
- `format` (18 edge(s))
- `strip` (17 edge(s))
- `append` (14 edge(s))
- `getattr` (9 edge(s))
- `isinstance` (8 edge(s))
- `BaseModel` (6 edge(s))
- `model_copy` (5 edge(s))
- `len` (4 edge(s))
- `warning` (4 edge(s))
- `ValueError` (4 edge(s))
- `dumps` (3 edge(s))
- `round` (3 edge(s))
- `join` (3 edge(s))

### Incoming

- `backend/services/observability_analysis/llm.py` (8 edge(s))
- `backend/services/admin_org_gap.py` (5 edge(s))
- `backend/models/observability.py` (4 edge(s))
- `backend/services/observability_prompts.py` (4 edge(s))
- `backend/tests/test_admin_org_gap.py` (4 edge(s))
- `model_copy` (4 edge(s))
- `backend/services/litellm_service.py` (3 edge(s))
- `backend/services/observability_analysis/diagnoser.py` (3 edge(s))
- `backend/services/ragflow/chat.py` (3 edge(s))
- `backend/models/admin_org.py` (2 edge(s))
- `backend/models/analysis.py::AnalysisRunRequest` (2 edge(s))
- `EnrichmentResult` (2 edge(s))
- `SocAnalysisResult` (2 edge(s))
- `HunterSection` (2 edge(s))
- `JudgeVerdict` (2 edge(s))
