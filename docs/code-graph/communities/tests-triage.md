# tests-triage

## Overview

Community of 104 nodes

- **Size**: 104 nodes
- **Cohesion**: 0.2690
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| FrameworkMappingItem | Class | backend/models/analysis.py | 15-20 |
| JudgeVerdict | Class | backend/models/analysis.py | 23-32 |
| HunterSection | Class | backend/models/analysis.py | 35-43 |
| SocAnalysisResult | Class | backend/models/analysis.py | 144-184 |
| AnalysisRunRequest | Class | backend/models/analysis.py | 187-203 |
| DashboardKpis | Class | backend/models/dashboard.py | 10-16 |
| CountByVerdict | Class | backend/models/dashboard.py | 32-34 |
| CountByPriority | Class | backend/models/dashboard.py | 37-39 |
| TrackSplit | Class | backend/models/dashboard.py | 42-44 |
| SystemResources | Class | backend/models/dashboard.py | 54-59 |
| DashboardOverview | Class | backend/models/dashboard.py | 76-88 |
| EnrichmentResult | Class | backend/models/enrichment.py | 10-15 |
| McpAlertContext | Class | backend/models/mcp.py | 49-61 |
| TriageFactor | Class | backend/models/triage.py | 14-22 |
| TriageReport | Class | backend/models/triage.py | 25-36 |
| TriageOutcome | Class | backend/models/triage.py | 39-55 |
| _compute_health_score | Function | backend/services/platform/dashboard_overview.py | 45-55 |
| _collect_triage_items | Function | backend/services/platform/dashboard_overview.py | 72-75 |
| build_dashboard_overview | Function | backend/services/platform/dashboard_overview.py | 127-205 |
| collect_system_resources | Function | backend/services/platform/system_resources.py | 14-28 |
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
| build_risk_context | Function | backend/services/soc_analysis/soc_analysis_risk.py | 30-66 |
| _inventory_lines | Function | backend/services/soc_rag/compact_analysis.py | 19-28 |
| _rich_analysis_extra_lines | Function | backend/services/soc_rag/compact_analysis.py | 31-80 |
| compact_analysis_document | Function | backend/services/soc_rag/compact_analysis.py | 83-136 |
| compact_analysis_from_payload | Function | backend/services/soc_rag/compact_analysis.py | 139-188 |
| _payload_dict | Function | backend/services/soc_rag/sql_chat/enrich.py | 16-25 |
| _apply_triage_to_row | Function | backend/services/soc_rag/sql_chat/enrich.py | 28-38 |
| enrich_rows_with_triage | Function | backend/services/soc_rag/sql_chat/enrich.py | 41-77 |
| _ensure_pool | Function | backend/services/splunk_json_store/stats.py | 13-18 |
| fetch_record_counts_by_type | Function | backend/services/splunk_json_store/stats.py | 21-32 |
| fetch_total_records | Function | backend/services/splunk_json_store/stats.py | 35-40 |
| fetch_records_last_24h | Function | backend/services/splunk_json_store/stats.py | 43-53 |
| fetch_analyses_last_24h | Function | backend/services/splunk_json_store/stats.py | 56-67 |
| fetch_activity_by_day | Function | backend/services/splunk_json_store/stats.py | 70-185 |
| fetch_inventory_counts | Function | backend/services/splunk_json_store/stats.py | 188-194 |
| _norm_token | Function | backend/services/triage/triage_priority.py | 30-34 |
| map_judge_verdict_to_review | Function | backend/services/triage/triage_priority.py | 37-47 |
| confidence_to_score | Function | backend/services/triage/triage_priority.py | 50-58 |
| _priority_weight | Function | backend/services/triage/triage_priority.py | 61-69 |

*... and 54 more members.*

## Execution Flows

- **assemble_from_langgraph** (criticality: 0.77, depth: 8)
- **run_analysis** (criticality: 0.76, depth: 6)
- **agent_triage_endpoint** (criticality: 0.76, depth: 8)
- **run_routed_analysis_endpoint** (criticality: 0.74, depth: 7)
- **dashboard_overview** (criticality: 0.74, depth: 8)
- **list_triage_queue** (criticality: 0.73, depth: 6)
- **work** (criticality: 0.72, depth: 5)
- **build_fallback_soc_result** (criticality: 0.71, depth: 5)
- **run_soc_analysis_batch_by_sid_endpoint** (criticality: 0.71, depth: 4)
- **run_observability_analysis** (criticality: 0.71, depth: 5)
- *... and 5 more flows.*

## Dependencies

### Outgoing

- `get` (97 edge(s))
- `append` (43 edge(s))
- `format` (42 edge(s))
- `isinstance` (35 edge(s))
- `str` (30 edge(s))
- `patch` (28 edge(s))
- `BaseModel` (16 edge(s))
- `int` (16 edge(s))
- `model_validate` (13 edge(s))
- `any` (12 edge(s))
- `strip` (11 edge(s))
- `replace` (8 edge(s))
- `len` (7 edge(s))
- `acquire` (7 edge(s))
- `join` (6 edge(s))

### Incoming

- `patch` (28 edge(s))
- `backend/services/triage/triage_priority.py` (20 edge(s))
- `backend/tests/test_triage_priority.py` (10 edge(s))
- `backend/services/soc_analysis/framework_mapping.py` (7 edge(s))
- `backend/services/splunk_json_store/stats.py` (7 edge(s))
- `backend/models/dashboard.py` (6 edge(s))
- `get` (6 edge(s))
- `any` (6 edge(s))
- `backend/models/analysis.py` (5 edge(s))
- `len` (5 edge(s))
- `backend/tests/test_splunk_json_store.py` (5 edge(s))
- `backend/services/soc_rag/compact_analysis.py` (4 edge(s))
- `backend/tests/test_framework_mapping.py` (4 edge(s))
- `backend/config.py::Settings` (4 edge(s))
- `backend/services/splunk_json_store/__init__.py::persist_soc_investigation_phases` (4 edge(s))
