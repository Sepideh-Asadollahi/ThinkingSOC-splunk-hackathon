# services-domain

## Overview

Community of 59 nodes

- **Size**: 59 nodes
- **Cohesion**: 0.3484
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| is_public_ip | Function | backend/services/virustotal.py | 142-165 |
| _norm_key | Function | backend/services/virustotal.py | 168-169 |
| _split_mv | Function | backend/services/virustotal.py | 172-177 |
| _yield_scalar_values | Function | backend/services/virustotal.py | 180-191 |
| _extract_hashes_from_text | Function | backend/services/virustotal.py | 194-202 |
| _host_from_url | Function | backend/services/virustotal.py | 205-213 |
| domain_vt_skip_reason | Function | backend/services/virustotal.py | 216-236 |
| _maybe_domain | Function | backend/services/virustotal.py | 239-255 |
| _parse_vt_error_body | Function | backend/services/virustotal.py | 258-277 |
| _http_failure_reason | Function | backend/services/virustotal.py | 280-301 |
| _iter_alert_field_pairs | Function | backend/services/virustotal.py | 304-322 |
| walk | Function | backend/services/virustotal.py | 309-316 |
| extract_iocs | Function | backend/services/virustotal.py | 325-458 |
| cap | Function | backend/services/virustotal.py | 347-348 |
| add_hashes | Function | backend/services/virustotal.py | 350-360 |
| add_ips | Function | backend/services/virustotal.py | 362-368 |
| add_domains | Function | backend/services/virustotal.py | 370-377 |
| add_urls | Function | backend/services/virustotal.py | 379-385 |
| _url_id_base64 | Function | backend/services/virustotal.py | 461-463 |
| VirusTotalClient | Class | backend/services/virustotal.py | 466-576 |
| __init__ | Function | backend/services/virustotal.py | 467-470 |
| configured | Function | backend/services/virustotal.py | 472-473 |
| _headers | Function | backend/services/virustotal.py | 475-476 |
| _get_json | Function | backend/services/virustotal.py | 478-539 |
| file_report | Function | backend/services/virustotal.py | 541-546 |
| domain_report | Function | backend/services/virustotal.py | 548-561 |
| ip_report | Function | backend/services/virustotal.py | 563-568 |
| url_report | Function | backend/services/virustotal.py | 570-576 |
| enrich_virustotal | Function | backend/services/virustotal.py | 579-640 |
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

*... and 9 more members.*

## Execution Flows

- **work** (criticality: 0.72, depth: 5)

## Dependencies

### Outgoing

- `format` (15 edge(s))
- `len` (12 edge(s))
- `AsyncMock` (12 edge(s))
- `strip` (11 edge(s))
- `MagicMock` (10 edge(s))
- `append` (9 edge(s))
- `model_copy` (9 edge(s))
- `info` (8 edge(s))
- `lower` (7 edge(s))
- `isinstance` (7 edge(s))
- `startswith` (7 edge(s))
- `get` (5 edge(s))
- `str` (5 edge(s))
- `warning` (4 edge(s))
- `quote` (4 edge(s))

### Incoming

- `backend/services/virustotal.py` (21 edge(s))
- `AsyncMock` (12 edge(s))
- `MagicMock` (10 edge(s))
- `backend/tests/test_virustotal.py` (9 edge(s))
- `model_copy` (9 edge(s))
- `backend/tests/fixtures/virustotal_api.py` (4 edge(s))
- `patch` (4 edge(s))
- `configured` (2 edge(s))
- `domain_report` (2 edge(s))
- `any` (2 edge(s))
- `ip_report` (2 edge(s))
- `backend/services/soc_analysis_graph/nodes_canonical.py::work` (1 edge(s))
- `rstrip` (1 edge(s))
- `decode` (1 edge(s))
- `urlsafe_b64encode` (1 edge(s))
