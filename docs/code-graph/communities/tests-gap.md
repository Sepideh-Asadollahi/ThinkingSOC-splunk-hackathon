# tests-gap

## Overview

Community of 95 nodes

- **Size**: 95 nodes
- **Cohesion**: 0.2935
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| AdminOrgGapSuggestRequest | Class | backend/models/admin_org.py | 10-23 |
| AdminOrgGapSuggestResponse | Class | backend/models/admin_org.py | 26-32 |
| FrameworkMappingItem | Class | backend/models/analysis.py | 15-20 |
| JudgeVerdict | Class | backend/models/analysis.py | 23-32 |
| HunterSection | Class | backend/models/analysis.py | 35-43 |
| SocAnalysisResult | Class | backend/models/analysis.py | 144-184 |
| AnalysisRunRequest | Class | backend/models/analysis.py | 187-203 |
| EnrichmentResult | Class | backend/models/enrichment.py | 10-15 |
| TriageFactor | Class | backend/models/triage.py | 14-22 |
| TriageReport | Class | backend/models/triage.py | 25-36 |
| TriageOutcome | Class | backend/models/triage.py | 39-55 |
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
| _parse_hunter_mcp | Function | backend/services/soc_analysis/assembly.py | 25-31 |
| _parse_judge_mcp | Function | backend/services/soc_analysis/assembly.py | 34-40 |
| assemble_from_langgraph | Function | backend/services/soc_analysis/assembly.py | 43-126 |
| build_fallback_soc_result | Function | backend/services/soc_analysis/fallback_result.py | 23-98 |
| _norm_framework | Function | backend/services/soc_analysis/framework_mapping.py | 23-24 |
| is_mitre_framework | Function | backend/services/soc_analysis/framework_mapping.py | 27-29 |
| is_kill_chain_framework | Function | backend/services/soc_analysis/framework_mapping.py | 32-34 |
| parse_framework_mapping_items | Function | backend/services/soc_analysis/framework_mapping.py | 37-61 |
| default_dual_framework_fallback | Function | backend/services/soc_analysis/framework_mapping.py | 64-80 |
| _infer_kill_chain_phase | Function | backend/services/soc_analysis/framework_mapping.py | 83-97 |
| ensure_mitre_and_kill_chain | Function | backend/services/soc_analysis/framework_mapping.py | 100-137 |
| load_admin_org_gap_system_prompt | Function | backend/services/soc_analysis/soc_analysis_prompts.py | 45-46 |
| build_risk_context | Function | backend/services/soc_analysis/soc_analysis_risk.py | 30-66 |
| _inventory_lines | Function | backend/services/soc_rag/compact_analysis.py | 19-28 |
| _rich_analysis_extra_lines | Function | backend/services/soc_rag/compact_analysis.py | 31-80 |
| compact_analysis_document | Function | backend/services/soc_rag/compact_analysis.py | 83-136 |
| compact_analysis_from_payload | Function | backend/services/soc_rag/compact_analysis.py | 139-188 |
| _payload_dict | Function | backend/services/soc_rag/sql_chat/enrich.py | 16-25 |
| _apply_triage_to_row | Function | backend/services/soc_rag/sql_chat/enrich.py | 28-38 |
| enrich_rows_with_triage | Function | backend/services/soc_rag/sql_chat/enrich.py | 41-77 |
| _norm_token | Function | backend/services/triage/triage_priority.py | 30-34 |
| map_judge_verdict_to_review | Function | backend/services/triage/triage_priority.py | 37-47 |
| confidence_to_score | Function | backend/services/triage/triage_priority.py | 50-58 |
| _priority_weight | Function | backend/services/triage/triage_priority.py | 61-69 |
| _impact_weight | Function | backend/services/triage/triage_priority.py | 72-80 |
| _inventory_risk_bonus | Function | backend/services/triage/triage_priority.py | 83-98 |
| _enrichment_penalty | Function | backend/services/triage/triage_priority.py | 101-109 |
| investigation_priority_from_score | Function | backend/services/triage/triage_priority.py | 112-119 |
| _base_score_for_review | Function | backend/services/triage/triage_priority.py | 122-127 |

*... and 45 more members.*

## Execution Flows

- **admin_org_gap_suggest** (criticality: 0.80, depth: 5)
- **assemble_from_langgraph** (criticality: 0.77, depth: 8)
- **run_analysis** (criticality: 0.76, depth: 6)
- **agent_triage_endpoint** (criticality: 0.75, depth: 8)
- **run_post_ingest** (criticality: 0.75, depth: 8)
- **run_routed_analysis_endpoint** (criticality: 0.74, depth: 7)
- **dashboard_overview** (criticality: 0.74, depth: 8)
- **list_triage_queue** (criticality: 0.73, depth: 6)
- **work** (criticality: 0.72, depth: 5)
- **run_soc_analysis_batch_by_sid_endpoint** (criticality: 0.71, depth: 4)
- *... and 7 more flows.*

## Dependencies

### Outgoing

- `get` (86 edge(s))
- `format` (48 edge(s))
- `append` (42 edge(s))
- `str` (37 edge(s))
- `isinstance` (32 edge(s))
- `strip` (18 edge(s))
- `patch` (15 edge(s))
- `any` (13 edge(s))
- `BaseModel` (11 edge(s))
- `model_validate` (10 edge(s))
- `replace` (8 edge(s))
- `lower` (7 edge(s))
- `join` (7 edge(s))
- `len` (6 edge(s))
- `setdefault` (5 edge(s))

### Incoming

- `backend/services/triage/triage_priority.py` (20 edge(s))
- `patch` (15 edge(s))
- `backend/services/soc_analysis/admin_org_gap.py` (10 edge(s))
- `backend/tests/test_triage_priority.py` (10 edge(s))
- `backend/tests/test_admin_org_gap.py` (9 edge(s))
- `backend/services/soc_analysis/framework_mapping.py` (7 edge(s))
- `any` (6 edge(s))
- `backend/models/analysis.py` (5 edge(s))
- `backend/tests/test_splunk_json_store.py` (5 edge(s))
- `backend/services/soc_rag/compact_analysis.py` (4 edge(s))
- `backend/tests/test_framework_mapping.py` (4 edge(s))
- `backend/config.py::Settings` (4 edge(s))
- `backend/services/splunk_json_store/__init__.py::persist_soc_investigation_phases` (4 edge(s))
- `backend/services/alert/agent_triage.py::run_agent_triage` (3 edge(s))
- `backend/models/triage.py` (3 edge(s))
