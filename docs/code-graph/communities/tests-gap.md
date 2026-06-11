# tests-gap

## Overview

Community of 113 nodes

- **Size**: 113 nodes
- **Cohesion**: 0.1973
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| ChatCompletionResponse | Class | backend/api/routes/llm.py | 38-42 |
| llm_chat | Function | backend/api/routes/llm.py | 65-136 |
| soc_chat | Function | backend/api/routes/soc_chat.py | 186-240 |
| AdminOrgGapSuggestRequest | Class | backend/models/admin_org.py | 10-23 |
| AdminOrgGapSuggestResponse | Class | backend/models/admin_org.py | 26-32 |
| RootCauseHypothesis | Class | backend/models/observability.py | 29-33 |
| DiagnoserSection | Class | backend/models/observability.py | 36-38 |
| ResponderSection | Class | backend/models/observability.py | 41-43 |
| OpsJudgeVerdict | Class | backend/models/observability.py | 46-52 |
| _truncate_saia_prompt | Function | backend/services/investigation/saia_prompt_prepare.py | 24-30 |
| _compact_alert_for_prepare | Function | backend/services/investigation/saia_prompt_prepare.py | 33-65 |
| _prepare_user_message | Function | backend/services/investigation/saia_prompt_prepare.py | 68-92 |
| prepare_saia_prompt_with_llm | Function | backend/services/investigation/saia_prompt_prepare.py | 95-149 |
| _cap_max_tokens | Function | backend/services/llm/litellm_service.py | 14-18 |
| LiteLLMNotConfiguredError | Class | backend/services/llm/litellm_service.py | 21-22 |
| LiteLLMProviderError | Class | backend/services/llm/litellm_service.py | 25-37 |
| __init__ | Function | backend/services/llm/litellm_service.py | 28-37 |
| provider_error_http_status | Function | backend/services/llm/litellm_service.py | 40-49 |
| _connection_indicators | Function | backend/services/llm/litellm_service.py | 52-67 |
| _map_litellm_exception | Function | backend/services/llm/litellm_service.py | 70-135 |
| _normalize_messages | Function | backend/services/llm/litellm_service.py | 138-148 |
| litellm_chat_completion | Function | backend/services/llm/litellm_service.py | 151-258 |
| saia_mcp_prompt_max_chars | Function | backend/services/llm/llm_context_budget.py | 52-54 |
| _append_thinking | Function | backend/services/llm/thinking_content.py | 45-48 |
| _extract_thinking_blocks | Function | backend/services/llm/thinking_content.py | 51-67 |
| _strip_tag_blocks | Function | backend/services/llm/thinking_content.py | 70-84 |
| split_thinking_and_answer | Function | backend/services/llm/thinking_content.py | 87-114 |
| split_litellm_message | Function | backend/services/llm/thinking_content.py | 117-161 |
| _to_float | Function | backend/services/observability_analysis/diagnoser.py | 10-16 |
| _build_searches | Function | backend/services/observability_analysis/diagnoser.py | 19-27 |
| build_diagnoser | Function | backend/services/observability_analysis/diagnoser.py | 30-101 |
| build_ops_judge | Function | backend/services/observability_analysis/judge.py | 8-46 |
| _context_json | Function | backend/services/observability_analysis/llm.py | 19-20 |
| _llm_json_response | Function | backend/services/observability_analysis/llm.py | 23-33 |
| _to_diagnoser | Function | backend/services/observability_analysis/llm.py | 36-58 |
| _to_responder | Function | backend/services/observability_analysis/llm.py | 61-70 |
| _to_ops_judge | Function | backend/services/observability_analysis/llm.py | 73-82 |
| build_diagnoser_llm | Function | backend/services/observability_analysis/llm.py | 85-89 |
| build_responder_llm | Function | backend/services/observability_analysis/llm.py | 92-96 |
| build_ops_judge_llm | Function | backend/services/observability_analysis/llm.py | 99-103 |
| _load_prompt_file | Function | backend/services/observability_analysis/observability_prompts.py | 14-15 |
| load_observability_diagnoser_system_prompt | Function | backend/services/observability_analysis/observability_prompts.py | 18-19 |
| load_observability_responder_system_prompt | Function | backend/services/observability_analysis/observability_prompts.py | 22-23 |
| load_observability_ops_judge_system_prompt | Function | backend/services/observability_analysis/observability_prompts.py | 26-27 |
| build_responder | Function | backend/services/observability_analysis/responder.py | 8-27 |
| _truncate | Function | backend/services/soc_analysis/admin_org_gap.py | 54-60 |
| _alert_text_blob | Function | backend/services/soc_analysis/admin_org_gap.py | 63-80 |
| _host_label | Function | backend/services/soc_analysis/admin_org_gap.py | 83-92 |
| _detect_process_org_gap | Function | backend/services/soc_analysis/admin_org_gap.py | 95-111 |
| _weak_identity | Function | backend/services/soc_analysis/admin_org_gap.py | 114-115 |

*... and 63 more members.*

## Execution Flows

- **admin_org_gap_suggest** (criticality: 0.80, depth: 5)
- **assistant_spl_suggest** (criticality: 0.77, depth: 9)
- **assemble_from_langgraph** (criticality: 0.77, depth: 8)
- **run_analysis** (criticality: 0.76, depth: 6)
- **agent_triage_endpoint** (criticality: 0.76, depth: 8)
- **soc_chat** (criticality: 0.75, depth: 5)
- **run_routed_analysis_endpoint** (criticality: 0.74, depth: 7)
- **work** (criticality: 0.74, depth: 6)
- **classify_alert_endpoint** (criticality: 0.73, depth: 6)
- **review_spl_from_mcp_with_llm** (criticality: 0.73, depth: 5)
- *... and 8 more flows.*

## Dependencies

### Outgoing

- `get` (82 edge(s))
- `str` (74 edge(s))
- `strip` (61 edge(s))
- `len` (50 edge(s))
- `format` (50 edge(s))
- `info` (38 edge(s))
- `append` (37 edge(s))
- `isinstance` (27 edge(s))
- `lower` (22 edge(s))
- `warning` (18 edge(s))
- `getattr` (17 edge(s))
- `join` (15 edge(s))
- `int` (12 edge(s))
- `perf_counter` (10 edge(s))
- `HTTPException` (9 edge(s))

### Incoming

- `backend/services/soc_analysis/admin_org_gap.py` (10 edge(s))
- `backend/services/llm/litellm_service.py` (8 edge(s))
- `backend/services/observability_analysis/llm.py` (8 edge(s))
- `backend/services/soc_analysis/soc_analysis_json.py` (8 edge(s))
- `lower` (8 edge(s))
- `backend/tests/test_soc_analysis_json.py` (7 edge(s))
- `backend/services/soc_rag/chat.py` (6 edge(s))
- `backend/services/soc_rag/sql_chat/answer.py` (6 edge(s))
- `backend/services/soc_rag/sql_chat/generate.py` (6 edge(s))
- `backend/tests/test_admin_org_gap.py` (6 edge(s))
- `backend/services/llm/thinking_content.py` (5 edge(s))
- `patch` (5 edge(s))
- `backend/models/observability.py` (4 edge(s))
- `backend/services/investigation/saia_prompt_prepare.py` (4 edge(s))
- `backend/services/observability_analysis/observability_prompts.py` (4 edge(s))
