# tests-vt

## Overview

Community of 95 nodes

- **Size**: 95 nodes
- **Cohesion**: 0.3280
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| work | Function | backend/services/soc_analysis_graph/nodes_canonical.py | 72-93 |
| _analyst_verdict_from_vt_stats | Function | backend/services/threat_intel/threat_intel_compact.py | 20-28 |
| _compact_vt_ioc_display_entry | Function | backend/services/threat_intel/threat_intel_compact.py | 31-72 |
| _compact_vt_ioc_entry | Function | backend/services/threat_intel/threat_intel_compact.py | 75-110 |
| _is_significant_finding | Function | backend/services/threat_intel/threat_intel_compact.py | 113-130 |
| _count_checked_iocs | Function | backend/services/threat_intel/threat_intel_compact.py | 133-145 |
| _build_note | Function | backend/services/threat_intel/threat_intel_compact.py | 148-164 |
| compact_threat_intel_for_analysis | Function | backend/services/threat_intel/threat_intel_compact.py | 167-221 |
| is_public_ip | Function | backend/services/threat_intel/virustotal.py | 153-176 |
| _norm_key | Function | backend/services/threat_intel/virustotal.py | 179-180 |
| _split_mv | Function | backend/services/threat_intel/virustotal.py | 183-188 |
| _yield_scalar_values | Function | backend/services/threat_intel/virustotal.py | 191-202 |
| _extract_hashes_from_text | Function | backend/services/threat_intel/virustotal.py | 205-213 |
| _host_from_url | Function | backend/services/threat_intel/virustotal.py | 216-224 |
| domain_vt_skip_reason | Function | backend/services/threat_intel/virustotal.py | 227-253 |
| _maybe_domain | Function | backend/services/threat_intel/virustotal.py | 256-272 |
| _parse_vt_error_body | Function | backend/services/threat_intel/virustotal.py | 275-294 |
| _http_failure_reason | Function | backend/services/threat_intel/virustotal.py | 297-318 |
| _iter_alert_field_pairs | Function | backend/services/threat_intel/virustotal.py | 321-339 |
| walk | Function | backend/services/threat_intel/virustotal.py | 326-333 |
| extract_iocs | Function | backend/services/threat_intel/virustotal.py | 342-479 |
| cap | Function | backend/services/threat_intel/virustotal.py | 366-367 |
| add_hashes | Function | backend/services/threat_intel/virustotal.py | 369-379 |
| add_ips | Function | backend/services/threat_intel/virustotal.py | 381-387 |
| add_domains | Function | backend/services/threat_intel/virustotal.py | 389-399 |
| add_urls | Function | backend/services/threat_intel/virustotal.py | 401-407 |
| _url_id_base64 | Function | backend/services/threat_intel/virustotal.py | 482-484 |
| VirusTotalClient | Class | backend/services/threat_intel/virustotal.py | 487-597 |
| __init__ | Function | backend/services/threat_intel/virustotal.py | 488-491 |
| configured | Function | backend/services/threat_intel/virustotal.py | 493-494 |
| _headers | Function | backend/services/threat_intel/virustotal.py | 496-497 |
| _get_json | Function | backend/services/threat_intel/virustotal.py | 499-560 |
| file_report | Function | backend/services/threat_intel/virustotal.py | 562-567 |
| domain_report | Function | backend/services/threat_intel/virustotal.py | 569-582 |
| ip_report | Function | backend/services/threat_intel/virustotal.py | 584-589 |
| url_report | Function | backend/services/threat_intel/virustotal.py | 591-597 |
| enrich_virustotal | Function | backend/services/threat_intel/virustotal.py | 600-661 |
| _as_int | Function | backend/services/threat_intel/virustotal_schema.py | 47-51 |
| normalize_last_analysis_stats | Function | backend/services/threat_intel/virustotal_schema.py | 54-66 |
| normalize_total_votes | Function | backend/services/threat_intel/virustotal_schema.py | 69-72 |
| extract_vt_object | Function | backend/services/threat_intel/virustotal_schema.py | 75-97 |
| build_vt_summary | Function | backend/services/threat_intel/virustotal_schema.py | 100-136 |
| stats_imply_malicious | Function | backend/services/threat_intel/virustotal_schema.py | 139-140 |
| stats_imply_suspicious | Function | backend/services/threat_intel/virustotal_schema.py | 143-144 |
| vt_ip_response | Function | backend/tests/fixtures/virustotal_api.py | 8-28 |
| vt_domain_response | Function | backend/tests/fixtures/virustotal_api.py | 31-51 |
| vt_file_response | Function | backend/tests/fixtures/virustotal_api.py | 54-78 |
| vt_url_response | Function | backend/tests/fixtures/virustotal_api.py | 81-102 |
| test_compact_filters_clean_iocs | Test | backend/tests/test_threat_intel_compact.py | 6-33 |
| test_compact_keeps_malicious_iocs | Test | backend/tests/test_threat_intel_compact.py | 36-75 |

*... and 45 more members.*

## Execution Flows

- **assemble_from_langgraph** (criticality: 0.77, depth: 8)
- **work** (criticality: 0.72, depth: 5)

## Dependencies

### Outgoing

- `get` (90 edge(s))
- `isinstance` (33 edge(s))
- `format` (21 edge(s))
- `len` (20 edge(s))
- `append` (12 edge(s))
- `str` (12 edge(s))
- `AsyncMock` (12 edge(s))
- `strip` (11 edge(s))
- `MagicMock` (10 edge(s))
- `model_copy` (9 edge(s))
- `info` (8 edge(s))
- `int` (7 edge(s))
- `lower` (7 edge(s))
- `startswith` (7 edge(s))
- `list` (4 edge(s))

### Incoming

- `backend/services/threat_intel/virustotal.py` (21 edge(s))
- `AsyncMock` (12 edge(s))
- `MagicMock` (10 edge(s))
- `backend/tests/test_virustotal.py` (9 edge(s))
- `model_copy` (9 edge(s))
- `backend/tests/test_virustotal_schema.py` (9 edge(s))
- `backend/services/threat_intel/threat_intel_compact.py` (7 edge(s))
- `backend/services/threat_intel/virustotal_schema.py` (7 edge(s))
- `backend/tests/test_threat_intel_compact.py` (6 edge(s))
- `backend/tests/fixtures/virustotal_api.py` (4 edge(s))
- `len` (4 edge(s))
- `patch` (4 edge(s))
- `backend/services/soc_analysis_graph/nodes_canonical.py` (3 edge(s))
- `configured` (2 edge(s))
- `domain_report` (2 edge(s))
