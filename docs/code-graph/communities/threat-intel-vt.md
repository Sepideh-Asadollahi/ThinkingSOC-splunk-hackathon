# threat-intel-vt

## Overview

Community of 70 nodes

- **Size**: 70 nodes
- **Cohesion**: 0.3574
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| TestIsPublicIp | Class | backend/tests/test_virustotal.py | 29-42 |
| test_public_ipv4 | Test | backend/tests/test_virustotal.py | 30-32 |
| test_private_and_special | Test | backend/tests/test_virustotal.py | 34-38 |
| test_invalid | Test | backend/tests/test_virustotal.py | 40-42 |
| TestUrlHelpers | Class | backend/tests/test_virustotal.py | 45-58 |
| test_url_id_base64_matches_vt_spec | Test | backend/tests/test_virustotal.py | 46-49 |
| test_host_from_url | Test | backend/tests/test_virustotal.py | 51-53 |
| test_maybe_domain | Test | backend/tests/test_virustotal.py | 55-58 |
| TestExtractIocs | Class | backend/tests/test_virustotal.py | 61-88 |
| test_empty_when_max_zero | Test | backend/tests/test_virustotal.py | 62-64 |
| test_priority_hash_before_ip_when_trimmed | Test | backend/tests/test_virustotal.py | 66-74 |
| test_src_dest_hostname_goes_to_domain | Test | backend/tests/test_virustotal.py | 76-79 |
| test_url_yields_domain_from_host | Test | backend/tests/test_virustotal.py | 81-88 |
| TestDomainVtSkip | Class | backend/tests/test_virustotal.py | 91-100 |
| test_example_tld_skipped | Test | backend/tests/test_virustotal.py | 92-95 |
| test_short_hostname_skipped | Test | backend/tests/test_virustotal.py | 97-100 |
| TestVirusTotalClient | Class | backend/tests/test_virustotal.py | 103-188 |
| test_configured_requires_key | Test | backend/tests/test_virustotal.py | 104-108 |
| test_get_json_404 | Test | backend/tests/test_virustotal.py | 111-127 |
| test_domain_report_skips_example_without_http | Test | backend/tests/test_virustotal.py | 130-139 |
| test_get_json_400_logs_detail | Test | backend/tests/test_virustotal.py | 142-167 |
| test_get_json_success | Test | backend/tests/test_virustotal.py | 170-188 |
| test_enrich_disabled | Test | backend/tests/test_virustotal.py | 192-195 |
| test_enrich_no_api_key | Test | backend/tests/test_virustotal.py | 199-203 |
| test_enrich_queries_each_ioc_type | Test | backend/tests/test_virustotal.py | 207-250 |
| fake_get_json | Function | backend/tests/test_virustotal.py | 218-227 |
| test_build_vt_summary_ip_official_shape | Test | backend/tests/test_virustotal_schema.py | 17-44 |
| test_build_vt_summary_file_extra_stat_keys | Test | backend/tests/test_virustotal_schema.py | 75-105 |
| test_build_vt_summary_domain | Test | backend/tests/test_virustotal_schema.py | 108-132 |
| test_extract_vt_object_errors | Test | backend/tests/test_virustotal_schema.py | 135-144 |
| test_normalize_stats_ip_ignores_file_only_keys | Test | backend/tests/test_virustotal_schema.py | 147-158 |
| test_build_vt_summary_returns_none_on_bad_envelope | Test | backend/tests/test_virustotal_schema.py | 166-168 |
| _as_int | Function | backend/services/threat_intel/virustotal_schema.py | 47-51 |
| normalize_last_analysis_stats | Function | backend/services/threat_intel/virustotal_schema.py | 54-66 |
| normalize_total_votes | Function | backend/services/threat_intel/virustotal_schema.py | 69-72 |
| extract_vt_object | Function | backend/services/threat_intel/virustotal_schema.py | 75-97 |
| build_vt_summary | Function | backend/services/threat_intel/virustotal_schema.py | 100-136 |
| is_public_ip | Function | backend/services/threat_intel/virustotal.py | 142-165 |
| _norm_key | Function | backend/services/threat_intel/virustotal.py | 168-169 |
| _split_mv | Function | backend/services/threat_intel/virustotal.py | 172-177 |
| _yield_scalar_values | Function | backend/services/threat_intel/virustotal.py | 180-191 |
| _extract_hashes_from_text | Function | backend/services/threat_intel/virustotal.py | 194-202 |
| _host_from_url | Function | backend/services/threat_intel/virustotal.py | 205-213 |
| domain_vt_skip_reason | Function | backend/services/threat_intel/virustotal.py | 216-236 |
| _maybe_domain | Function | backend/services/threat_intel/virustotal.py | 239-255 |
| _parse_vt_error_body | Function | backend/services/threat_intel/virustotal.py | 258-277 |
| _http_failure_reason | Function | backend/services/threat_intel/virustotal.py | 280-301 |
| _iter_alert_field_pairs | Function | backend/services/threat_intel/virustotal.py | 304-322 |
| walk | Function | backend/services/threat_intel/virustotal.py | 309-316 |
| extract_iocs | Function | backend/services/threat_intel/virustotal.py | 325-458 |

*... and 20 more members.*

## Execution Flows

- **work** (criticality: 0.72, depth: 5)

## Dependencies

### Outgoing

- `get` (23 edge(s))
- `format` (15 edge(s))
- `isinstance` (15 edge(s))
- `len` (12 edge(s))
- `AsyncMock` (12 edge(s))
- `strip` (11 edge(s))
- `MagicMock` (10 edge(s))
- `append` (9 edge(s))
- `model_copy` (9 edge(s))
- `info` (8 edge(s))
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
- `backend/tests/test_virustotal_schema.py` (6 edge(s))
- `backend/services/threat_intel/virustotal_schema.py` (5 edge(s))
- `backend/tests/fixtures/virustotal_api.py` (4 edge(s))
- `patch` (4 edge(s))
- `configured` (2 edge(s))
- `domain_report` (2 edge(s))
- `any` (2 edge(s))
- `ip_report` (2 edge(s))
- `backend/services/soc_analysis_graph/nodes_canonical.py::work` (1 edge(s))
- `backend/tests/test_virustotal_schema.py::test_build_vt_summary_url_includes_categories` (1 edge(s))
