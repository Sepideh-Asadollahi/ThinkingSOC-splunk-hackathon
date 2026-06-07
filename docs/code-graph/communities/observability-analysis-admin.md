# observability-analysis-admin

## Overview

Community of 33 nodes

- **Size**: 33 nodes
- **Cohesion**: 0.2553
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| AdminOrgGapSuggestRequest | Class | backend/models/admin_org.py | 10-21 |
| AdminOrgGapSuggestResponse | Class | backend/models/admin_org.py | 24-30 |
| RootCauseHypothesis | Class | backend/models/observability.py | 28-32 |
| DiagnoserSection | Class | backend/models/observability.py | 35-37 |
| ResponderSection | Class | backend/models/observability.py | 40-42 |
| OpsJudgeVerdict | Class | backend/models/observability.py | 45-51 |
| load_admin_org_gap_system_prompt | Function | backend/services/soc_analysis_prompts.py | 45-46 |
| parse_llm_json_response | Function | backend/services/soc_analysis_json.py | 12-17 |
| _load_prompt_file | Function | backend/services/observability_prompts.py | 14-15 |
| load_observability_diagnoser_system_prompt | Function | backend/services/observability_prompts.py | 18-19 |
| load_observability_responder_system_prompt | Function | backend/services/observability_prompts.py | 22-23 |
| load_observability_ops_judge_system_prompt | Function | backend/services/observability_prompts.py | 26-27 |
| _fallback_response | Function | backend/services/admin_org_gap.py | 18-41 |
| suggest_admin_org_gap | Function | backend/services/admin_org_gap.py | 44-117 |
| LiteLLMNotConfiguredError | Class | backend/services/litellm_service.py | 13-14 |
| _normalize_messages | Function | backend/services/litellm_service.py | 17-27 |
| litellm_chat_completion | Function | backend/services/litellm_service.py | 30-104 |
| test_suggest_admin_org_gap_fallback_no_identity | Test | backend/tests/test_admin_org_gap.py | 15-26 |
| test_suggest_admin_org_gap_fallback_with_asset | Test | backend/tests/test_admin_org_gap.py | 30-37 |
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
| llm_json_response | Function | backend/services/soc_analysis_graph/llm.py | 12-29 |

## Execution Flows

- **admin_org_gap_suggest** (criticality: 0.80, depth: 3)
- **splunk_ingest** (criticality: 0.75, depth: 7)
- **agent_triage_endpoint** (criticality: 0.74, depth: 6)
- **assistant_spl_suggest** (criticality: 0.73, depth: 5)
- **run_routed_analysis_endpoint** (criticality: 0.73, depth: 4)
- **classify_alert_endpoint** (criticality: 0.71, depth: 3)
- **build_diagnoser_llm** (criticality: 0.68, depth: 3)
- **build_responder_llm** (criticality: 0.68, depth: 3)
- **build_ops_judge_llm** (criticality: 0.68, depth: 3)
- **llm_chat** (criticality: 0.63, depth: 3)
- *... and 3 more flows.*

## Dependencies

### Outgoing

- `get` (28 edge(s))
- `str` (20 edge(s))
- `format` (15 edge(s))
- `strip` (14 edge(s))
- `append` (12 edge(s))
- `getattr` (9 edge(s))
- `BaseModel` (6 edge(s))
- `isinstance` (6 edge(s))
- `warning` (3 edge(s))
- `ValueError` (3 edge(s))
- `dumps` (2 edge(s))
- `max` (2 edge(s))
- `len` (2 edge(s))
- `model_copy` (2 edge(s))
- `bool` (1 edge(s))

### Incoming

- `backend/services/observability_analysis/llm.py` (8 edge(s))
- `backend/models/observability.py` (4 edge(s))
- `backend/services/observability_prompts.py` (4 edge(s))
- `backend/services/litellm_service.py` (3 edge(s))
- `backend/services/observability_analysis/diagnoser.py` (3 edge(s))
- `backend/models/admin_org.py` (2 edge(s))
- `backend/services/admin_org_gap.py` (2 edge(s))
- `backend/tests/test_admin_org_gap.py` (2 edge(s))
- `model_copy` (2 edge(s))
- `backend/api/routes/admin_org.py::admin_org_gap_suggest` (1 edge(s))
- `backend/services/alert_classifier_llm.py::classify_alert_hybrid` (1 edge(s))
- `backend/api/routes/llm.py::llm_chat` (1 edge(s))
- `backend/services/observability_analysis/judge.py` (1 edge(s))
- `backend/services/observability_analysis/responder.py` (1 edge(s))
- `backend/services/spl_mcp_review.py::review_spl_from_mcp_with_llm` (1 edge(s))
