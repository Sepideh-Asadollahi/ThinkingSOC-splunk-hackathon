# tests-vt

## Overview

Community of 77 nodes

- **Size**: 77 nodes
- **Cohesion**: 0.3784
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
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
| vt_ip_response | Function | backend/tests/fixtures/virustotal_api.py | 8-28 |
| vt_domain_response | Function | backend/tests/fixtures/virustotal_api.py | 31-51 |
| vt_file_response | Function | backend/tests/fixtures/virustotal_api.py | 54-78 |
| vt_url_response | Function | backend/tests/fixtures/virustotal_api.py | 81-102 |
| TestIsPublicIp | Class | backend/tests/test_virustotal.py | 29-42 |
| test_public_ipv4 | Test | backend/tests/test_virustotal.py | 30-32 |
| test_private_and_special | Test | backend/tests/test_virustotal.py | 34-38 |
| test_invalid | Test | backend/tests/test_virustotal.py | 40-42 |
| TestUrlHelpers | Class | backend/tests/test_virustotal.py | 45-58 |
| test_url_id_base64_matches_vt_spec | Test | backend/tests/test_virustotal.py | 46-49 |
| test_host_from_url | Test | backend/tests/test_virustotal.py | 51-53 |
| test_maybe_domain | Test | backend/tests/test_virustotal.py | 55-58 |
| TestExtractIocs | Class | backend/tests/test_virustotal.py | 61-126 |
| test_empty_when_max_zero | Test | backend/tests/test_virustotal.py | 62-64 |
| test_priority_hash_before_ip_when_trimmed | Test | backend/tests/test_virustotal.py | 66-74 |
| test_src_dest_hostname_not_domain_only_public_ip | Test | backend/tests/test_virustotal.py | 76-80 |

*... and 27 more members.*

## Execution Flows

- **work** (criticality: 0.72, depth: 5)

## Dependencies

### Outgoing

- `get` (23 edge(s))
- `format` (16 edge(s))
- `isinstance` (15 edge(s))
- `len` (12 edge(s))
- `AsyncMock` (12 edge(s))
- `strip` (11 edge(s))
- `MagicMock` (10 edge(s))
- `model_copy` (9 edge(s))
- `info` (8 edge(s))
- `append` (8 edge(s))
- `lower` (7 edge(s))
- `startswith` (7 edge(s))
- `str` (6 edge(s))
- `warning` (4 edge(s))
- `quote` (4 edge(s))

### Incoming

- `backend/services/threat_intel/virustotal.py` (21 edge(s))
- `AsyncMock` (12 edge(s))
- `MagicMock` (10 edge(s))
- `backend/tests/test_virustotal.py` (9 edge(s))
- `model_copy` (9 edge(s))
- `backend/tests/test_virustotal_schema.py` (7 edge(s))
- `backend/services/threat_intel/virustotal_schema.py` (5 edge(s))
- `backend/tests/fixtures/virustotal_api.py` (4 edge(s))
- `patch` (4 edge(s))
- `configured` (2 edge(s))
- `domain_report` (2 edge(s))
- `any` (2 edge(s))
- `ip_report` (2 edge(s))
- `backend/services/soc_analysis_graph/nodes_canonical.py::work` (1 edge(s))
- `rstrip` (1 edge(s))
