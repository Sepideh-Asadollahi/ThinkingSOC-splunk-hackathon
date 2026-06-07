# services-report

## Overview

Community of 27 nodes

- **Size**: 27 nodes
- **Cohesion**: 0.3516
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| is_public_ip | Function | backend/services/virustotal.py | 133-156 |
| _norm_key | Function | backend/services/virustotal.py | 159-160 |
| _split_mv | Function | backend/services/virustotal.py | 163-168 |
| _yield_scalar_values | Function | backend/services/virustotal.py | 171-182 |
| _extract_hashes_from_text | Function | backend/services/virustotal.py | 185-193 |
| _host_from_url | Function | backend/services/virustotal.py | 196-204 |
| _maybe_domain | Function | backend/services/virustotal.py | 207-223 |
| _iter_alert_field_pairs | Function | backend/services/virustotal.py | 226-244 |
| walk | Function | backend/services/virustotal.py | 231-238 |
| extract_iocs | Function | backend/services/virustotal.py | 247-380 |
| cap | Function | backend/services/virustotal.py | 269-270 |
| add_hashes | Function | backend/services/virustotal.py | 272-282 |
| add_ips | Function | backend/services/virustotal.py | 284-290 |
| add_domains | Function | backend/services/virustotal.py | 292-299 |
| add_urls | Function | backend/services/virustotal.py | 301-307 |
| _url_id_base64 | Function | backend/services/virustotal.py | 383-385 |
| _vt_obj_summary | Function | backend/services/virustotal.py | 388-403 |
| VirusTotalClient | Class | backend/services/virustotal.py | 406-440 |
| __init__ | Function | backend/services/virustotal.py | 407-410 |
| configured | Function | backend/services/virustotal.py | 412-413 |
| _headers | Function | backend/services/virustotal.py | 415-416 |
| _get_json | Function | backend/services/virustotal.py | 418-428 |
| file_report | Function | backend/services/virustotal.py | 430-431 |
| domain_report | Function | backend/services/virustotal.py | 433-434 |
| ip_report | Function | backend/services/virustotal.py | 436-437 |
| url_report | Function | backend/services/virustotal.py | 439-440 |
| enrich_virustotal | Function | backend/services/virustotal.py | 443-496 |

## Execution Flows

- **work** (criticality: 0.72, depth: 5)

## Dependencies

### Outgoing

- `get` (13 edge(s))
- `len` (12 edge(s))
- `strip` (9 edge(s))
- `append` (9 edge(s))
- `lower` (6 edge(s))
- `format` (5 edge(s))
- `isinstance` (5 edge(s))
- `findall` (4 edge(s))
- `str` (3 edge(s))
- `getattr` (3 edge(s))
- `rstrip` (2 edge(s))
- `bool` (2 edge(s))
- `ip_address` (2 edge(s))
- `fullmatch` (2 edge(s))
- `startswith` (2 edge(s))

### Incoming

- `backend/services/virustotal.py` (19 edge(s))
- `backend/services/soc_analysis_graph/nodes_canonical.py::work` (1 edge(s))
