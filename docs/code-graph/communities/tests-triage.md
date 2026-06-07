# tests-triage

## Overview

Community of 144 nodes

- **Size**: 144 nodes
- **Cohesion**: 0.2759
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| Settings | Class | backend/config.py | 24-209 |
| AlertClassificationResult | Class | backend/models/agentic_ops.py | 15-23 |
| FrameworkMappingItem | Class | backend/models/analysis.py | 15-20 |
| JudgeVerdict | Class | backend/models/analysis.py | 23-32 |
| HunterSection | Class | backend/models/analysis.py | 35-43 |
| SocAnalysisResult | Class | backend/models/analysis.py | 144-184 |
| AnalysisRunRequest | Class | backend/models/analysis.py | 187-203 |
| EnrichmentResult | Class | backend/models/enrichment.py | 10-15 |
| McpAlertContext | Class | backend/models/mcp.py | 49-61 |
| TriageFactor | Class | backend/models/triage.py | 14-22 |
| TriageReport | Class | backend/models/triage.py | 25-36 |
| classify_alert_unavailable | Function | backend/services/alert/alert_classifier.py | 10-20 |
| classify_alert | Function | backend/services/alert/alert_classifier.py | 23-31 |
| default_investigation_time_window | Function | backend/services/investigation/spl_predict_pipeline.py | 39-42 |
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
| work | Function | backend/services/soc_analysis_graph/nodes_canonical.py | 72-93 |
| _inventory_lines | Function | backend/services/soc_rag/compact_analysis.py | 19-28 |
| _rich_analysis_extra_lines | Function | backend/services/soc_rag/compact_analysis.py | 31-80 |
| compact_analysis_document | Function | backend/services/soc_rag/compact_analysis.py | 83-136 |
| compact_analysis_from_payload | Function | backend/services/soc_rag/compact_analysis.py | 139-188 |
| _payload_dict | Function | backend/services/soc_rag/sql_chat/enrich.py | 16-25 |
| _apply_triage_to_row | Function | backend/services/soc_rag/sql_chat/enrich.py | 28-38 |
| enrich_rows_with_triage | Function | backend/services/soc_rag/sql_chat/enrich.py | 41-77 |
| _analyst_verdict_from_vt_stats | Function | backend/services/threat_intel/threat_intel_compact.py | 20-28 |
| _compact_vt_ioc_display_entry | Function | backend/services/threat_intel/threat_intel_compact.py | 31-72 |
| _compact_vt_ioc_entry | Function | backend/services/threat_intel/threat_intel_compact.py | 75-110 |
| _is_significant_finding | Function | backend/services/threat_intel/threat_intel_compact.py | 113-130 |
| _count_checked_iocs | Function | backend/services/threat_intel/threat_intel_compact.py | 133-145 |
| _build_note | Function | backend/services/threat_intel/threat_intel_compact.py | 148-164 |
| compact_threat_intel_for_analysis | Function | backend/services/threat_intel/threat_intel_compact.py | 167-221 |
| stats_imply_malicious | Function | backend/services/threat_intel/virustotal_schema.py | 139-140 |
| stats_imply_suspicious | Function | backend/services/threat_intel/virustotal_schema.py | 143-144 |
| _norm_token | Function | backend/services/triage/triage_priority.py | 30-34 |
| map_judge_verdict_to_review | Function | backend/services/triage/triage_priority.py | 37-47 |
| confidence_to_score | Function | backend/services/triage/triage_priority.py | 50-58 |
| _priority_weight | Function | backend/services/triage/triage_priority.py | 61-69 |
| _impact_weight | Function | backend/services/triage/triage_priority.py | 72-80 |
| _inventory_risk_bonus | Function | backend/services/triage/triage_priority.py | 83-98 |
| _enrichment_penalty | Function | backend/services/triage/triage_priority.py | 101-109 |

*... and 94 more members.*

## Execution Flows

- **assemble_from_langgraph** (criticality: 0.77, depth: 8)
- **run_analysis** (criticality: 0.76, depth: 6)
- **agent_triage_endpoint** (criticality: 0.75, depth: 8)
- **run_post_ingest** (criticality: 0.75, depth: 8)
- **run_routed_analysis_endpoint** (criticality: 0.74, depth: 7)
- **dashboard_overview** (criticality: 0.74, depth: 8)
- **classify_alert_endpoint** (criticality: 0.73, depth: 6)
- **list_triage_queue** (criticality: 0.73, depth: 6)
- **work** (criticality: 0.72, depth: 5)
- **run_soc_analysis_batch_by_sid_endpoint** (criticality: 0.71, depth: 4)
- *... and 11 more flows.*

## Dependencies

### Outgoing

- `get` (151 edge(s))
- `isinstance` (51 edge(s))
- `format` (47 edge(s))
- `append` (45 edge(s))
- `str` (33 edge(s))
- `patch` (27 edge(s))
- `len` (17 edge(s))
- `any` (12 edge(s))
- `strip` (11 edge(s))
- `BaseModel` (10 edge(s))
- `model_validate` (10 edge(s))
- `replace` (8 edge(s))
- `int` (8 edge(s))
- `join` (7 edge(s))
- `run` (7 edge(s))

### Incoming

- `patch` (21 edge(s))
- `backend/services/triage/triage_priority.py` (20 edge(s))
- `backend/tests/test_splunk_json_store.py` (17 edge(s))
- `len` (12 edge(s))
- `get` (10 edge(s))
- `backend/tests/test_alert_classifier_llm.py` (10 edge(s))
- `backend/tests/test_triage_priority.py` (10 edge(s))
- `backend/services/soc_analysis/framework_mapping.py` (7 edge(s))
- `backend/services/threat_intel/threat_intel_compact.py` (7 edge(s))
- `run` (7 edge(s))
- `any` (6 edge(s))
- `backend/tests/test_threat_intel_compact.py` (6 edge(s))
- `backend/models/analysis.py` (5 edge(s))
- `resolve_embedding_model` (5 edge(s))
- `backend/tests/test_config_env.py` (4 edge(s))
