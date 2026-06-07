# services-vt

## Overview

Community of 42 nodes

- **Size**: 42 nodes
- **Cohesion**: 0.2644
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| FrameworkMappingItem | Class | backend/models/analysis.py | 14-19 |
| _analyst_verdict_from_vt_stats | Function | backend/services/threat_intel_compact.py | 20-28 |
| _compact_vt_ioc_display_entry | Function | backend/services/threat_intel_compact.py | 31-72 |
| _compact_vt_ioc_entry | Function | backend/services/threat_intel_compact.py | 75-110 |
| _is_significant_finding | Function | backend/services/threat_intel_compact.py | 113-130 |
| _count_checked_iocs | Function | backend/services/threat_intel_compact.py | 133-145 |
| _build_note | Function | backend/services/threat_intel_compact.py | 148-164 |
| compact_threat_intel_for_analysis | Function | backend/services/threat_intel_compact.py | 167-221 |
| _as_int | Function | backend/services/virustotal_schema.py | 47-51 |
| normalize_last_analysis_stats | Function | backend/services/virustotal_schema.py | 54-66 |
| normalize_total_votes | Function | backend/services/virustotal_schema.py | 69-72 |
| extract_vt_object | Function | backend/services/virustotal_schema.py | 75-97 |
| build_vt_summary | Function | backend/services/virustotal_schema.py | 100-136 |
| stats_imply_malicious | Function | backend/services/virustotal_schema.py | 139-140 |
| stats_imply_suspicious | Function | backend/services/virustotal_schema.py | 143-144 |
| _norm_framework | Function | backend/services/framework_mapping.py | 23-24 |
| is_mitre_framework | Function | backend/services/framework_mapping.py | 27-29 |
| is_kill_chain_framework | Function | backend/services/framework_mapping.py | 32-34 |
| parse_framework_mapping_items | Function | backend/services/framework_mapping.py | 37-61 |
| default_dual_framework_fallback | Function | backend/services/framework_mapping.py | 64-80 |
| _infer_kill_chain_phase | Function | backend/services/framework_mapping.py | 83-97 |
| ensure_mitre_and_kill_chain | Function | backend/services/framework_mapping.py | 100-137 |
| test_framework_labels_detected | Test | backend/tests/test_framework_mapping.py | 14-16 |
| test_default_dual_fallback_has_both | Test | backend/tests/test_framework_mapping.py | 19-23 |
| test_ensure_adds_missing_kill_chain | Test | backend/tests/test_framework_mapping.py | 26-40 |
| test_ensure_adds_missing_mitre | Test | backend/tests/test_framework_mapping.py | 43-57 |
| test_compact_filters_clean_iocs | Test | backend/tests/test_threat_intel_compact.py | 6-33 |
| test_compact_keeps_malicious_iocs | Test | backend/tests/test_threat_intel_compact.py | 36-75 |
| test_compact_disabled_vt | Test | backend/tests/test_threat_intel_compact.py | 78-82 |
| test_compact_significant_via_negative_reputation | Test | backend/tests/test_threat_intel_compact.py | 85-112 |
| test_compact_significant_via_community_votes | Test | backend/tests/test_threat_intel_compact.py | 115-137 |
| test_compact_passthrough_already_compact | Test | backend/tests/test_threat_intel_compact.py | 140-150 |
| test_build_vt_summary_ip_official_shape | Test | backend/tests/test_virustotal_schema.py | 17-44 |
| test_build_vt_summary_url_includes_categories | Test | backend/tests/test_virustotal_schema.py | 47-72 |
| test_build_vt_summary_file_extra_stat_keys | Test | backend/tests/test_virustotal_schema.py | 75-105 |
| test_build_vt_summary_domain | Test | backend/tests/test_virustotal_schema.py | 108-132 |
| test_extract_vt_object_errors | Test | backend/tests/test_virustotal_schema.py | 135-144 |
| test_normalize_stats_ip_ignores_file_only_keys | Test | backend/tests/test_virustotal_schema.py | 147-158 |
| test_stats_imply_suspicious_only_when_no_malicious | Test | backend/tests/test_virustotal_schema.py | 161-163 |
| test_build_vt_summary_returns_none_on_bad_envelope | Test | backend/tests/test_virustotal_schema.py | 166-168 |
| test_compact_preserves_vt_field_names | Test | backend/tests/test_virustotal_schema.py | 171-204 |
| assemble_from_langgraph | Function | backend/services/soc_analysis/assembly.py | 22-94 |

## Execution Flows

- **assemble_from_langgraph** (criticality: 0.73, depth: 5)
- **work** (criticality: 0.72, depth: 5)
- **build_fallback_soc_result** (criticality: 0.72, depth: 4)

## Dependencies

### Outgoing

- `get` (87 edge(s))
- `isinstance` (31 edge(s))
- `str` (21 edge(s))
- `any` (12 edge(s))
- `len` (9 edge(s))
- `append` (6 edge(s))
- `format` (5 edge(s))
- `strip` (4 edge(s))
- `sum` (3 edge(s))
- `int` (3 edge(s))
- `lower` (2 edge(s))
- `join` (2 edge(s))
- `list` (2 edge(s))
- `items` (2 edge(s))
- `BaseModel` (1 edge(s))

### Incoming

- `backend/tests/test_virustotal_schema.py` (9 edge(s))
- `backend/services/framework_mapping.py` (7 edge(s))
- `backend/services/threat_intel_compact.py` (7 edge(s))
- `backend/services/virustotal_schema.py` (7 edge(s))
- `any` (6 edge(s))
- `backend/tests/test_threat_intel_compact.py` (6 edge(s))
- `len` (5 edge(s))
- `backend/services/virustotal.py::enrich_virustotal` (4 edge(s))
- `backend/tests/test_framework_mapping.py` (4 edge(s))
- `backend/models/analysis.py` (1 edge(s))
- `backend/services/soc_analysis/fallback_result.py::build_fallback_soc_result` (1 edge(s))
- `backend/services/soc_analysis/assembly.py` (1 edge(s))
- `backend/services/soc_analysis_graph/nodes_canonical.py::work` (1 edge(s))
