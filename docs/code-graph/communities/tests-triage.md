# tests-triage

## Overview

Community of 175 nodes

- **Size**: 175 nodes
- **Cohesion**: 0.2812
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| AdminOrgGapSuggestRequest | Class | backend/models/admin_org.py | 10-23 |
| AdminOrgGapSuggestResponse | Class | backend/models/admin_org.py | 26-32 |
| FrameworkMappingItem | Class | backend/models/analysis.py | 15-20 |
| JudgeVerdict | Class | backend/models/analysis.py | 23-32 |
| HunterSection | Class | backend/models/analysis.py | 35-43 |
| EvidenceChain | Class | backend/models/analysis.py | 134-141 |
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
| EntityResolution | Class | backend/models/observability.py | 13-18 |
| TriageFactor | Class | backend/models/triage.py | 14-22 |
| TriageReport | Class | backend/models/triage.py | 25-36 |
| TriageOutcome | Class | backend/models/triage.py | 39-55 |
| _norm_str | Function | backend/services/alert/enrichment_resolver.py | 33-36 |
| _rows_matching_exact | Function | backend/services/alert/enrichment_resolver.py | 39-56 |
| _pick_asset_row | Function | backend/services/alert/enrichment_resolver.py | 59-69 |
| _pick_user_row | Function | backend/services/alert/enrichment_resolver.py | 72-75 |
| _match_assets | Function | backend/services/alert/enrichment_resolver.py | 78-95 |
| _match_users | Function | backend/services/alert/enrichment_resolver.py | 98-120 |
| _asset_criticality_rank | Function | backend/services/alert/enrichment_resolver.py | 123-127 |
| _user_risk_rank | Function | backend/services/alert/enrichment_resolver.py | 130-137 |
| _pick_relationship_for_user | Function | backend/services/alert/enrichment_resolver.py | 140-153 |
| _pick_relationship_for_asset | Function | backend/services/alert/enrichment_resolver.py | 156-169 |
| _apply_relationships | Function | backend/services/alert/enrichment_resolver.py | 172-209 |
| enrich_from_inventory | Function | backend/services/alert/enrichment_resolver.py | 212-256 |
| _norm | Function | backend/services/observability_analysis/entity.py | 12-13 |
| _find_asset_by_host_or_ip | Function | backend/services/observability_analysis/entity.py | 16-23 |
| build_entity_resolution | Function | backend/services/observability_analysis/entity.py | 26-60 |
| _compute_health_score | Function | backend/services/platform/dashboard_overview.py | 45-55 |
| _collect_triage_items | Function | backend/services/platform/dashboard_overview.py | 72-75 |
| build_dashboard_overview | Function | backend/services/platform/dashboard_overview.py | 127-205 |
| collect_system_resources | Function | backend/services/platform/system_resources.py | 14-28 |
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
| build_analysis_output | Function | backend/services/soc_analysis/analysis_audit.py | 149-170 |

*... and 125 more members.*

## Execution Flows

- **admin_org_gap_suggest** (criticality: 0.80, depth: 5)
- **assemble_from_langgraph** (criticality: 0.77, depth: 8)
- **run_analysis** (criticality: 0.76, depth: 6)
- **agent_triage_endpoint** (criticality: 0.76, depth: 8)
- **run_routed_analysis_endpoint** (criticality: 0.74, depth: 7)
- **dashboard_overview** (criticality: 0.74, depth: 8)
- **list_triage_queue** (criticality: 0.73, depth: 6)
- **work** (criticality: 0.72, depth: 5)
- **build_fallback_soc_result** (criticality: 0.71, depth: 5)
- **run_soc_analysis_batch_by_sid_endpoint** (criticality: 0.71, depth: 4)
- *... and 7 more flows.*

## Dependencies

### Outgoing

- `get` (203 edge(s))
- `format` (59 edge(s))
- `append` (55 edge(s))
- `isinstance` (53 edge(s))
- `str` (52 edge(s))
- `patch` (30 edge(s))
- `len` (27 edge(s))
- `strip` (24 edge(s))
- `int` (22 edge(s))
- `BaseModel` (20 edge(s))
- `lower` (18 edge(s))
- `model_validate` (13 edge(s))
- `any` (13 edge(s))
- `join` (9 edge(s))
- `replace` (8 edge(s))

### Incoming

- `patch` (30 edge(s))
- `backend/services/triage/triage_priority.py` (20 edge(s))
- `backend/services/alert/enrichment_resolver.py` (12 edge(s))
- `backend/services/soc_analysis/admin_org_gap.py` (10 edge(s))
- `backend/tests/test_triage_priority.py` (10 edge(s))
- `backend/tests/test_admin_org_gap.py` (9 edge(s))
- `backend/tests/test_enrichment_resolver.py` (9 edge(s))
- `len` (9 edge(s))
- `backend/services/soc_analysis/framework_mapping.py` (7 edge(s))
- `backend/services/splunk_json_store/stats.py` (7 edge(s))
- `backend/services/threat_intel/threat_intel_compact.py` (7 edge(s))
- `backend/models/analysis.py` (6 edge(s))
- `backend/models/dashboard.py` (6 edge(s))
- `get` (6 edge(s))
- `any` (6 edge(s))
