# services-row

## Overview

Community of 23 nodes

- **Size**: 23 nodes
- **Cohesion**: 0.2419
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| IdentityResolution | Class | backend/models/identity.py | 10-15 |
| EntityResolution | Class | backend/models/observability.py | 12-17 |
| _norm_str | Function | backend/services/identity_resolver.py | 12-15 |
| _rule_enabled | Function | backend/services/identity_resolver.py | 18-31 |
| _parse_priority | Function | backend/services/identity_resolver.py | 34-40 |
| _rows_matching_exact | Function | backend/services/identity_resolver.py | 43-61 |
| _pick_asset_row | Function | backend/services/identity_resolver.py | 64-81 |
| _pick_user_row | Function | backend/services/identity_resolver.py | 84-88 |
| resolve_identity | Function | backend/services/identity_resolver.py | 91-208 |
| _bump_conf | Function | backend/services/identity_resolver.py | 139-143 |
| find_user_row | Function | backend/services/soc_analysis_risk.py | 10-17 |
| find_asset_row | Function | backend/services/soc_analysis_risk.py | 20-27 |
| build_risk_context | Function | backend/services/soc_analysis_risk.py | 30-63 |
| persist_soc_analysis_to_splunk | Function | backend/services/splunk_json_store.py | 115-134 |
| _sample_tables | Function | backend/tests/test_identity_resolver.py | 8-41 |
| test_resolve_host_and_user | Test | backend/tests/test_identity_resolver.py | 44-50 |
| test_no_match_note | Test | backend/tests/test_identity_resolver.py | 53-59 |
| test_highest_criticality_pick | Test | backend/tests/test_identity_resolver.py | 62-83 |
| run_analysis | Function | backend/services/soc_analysis/runner.py | 22-106 |
| _norm | Function | backend/services/observability_analysis/entity.py | 12-13 |
| _find_asset_by_host_or_ip | Function | backend/services/observability_analysis/entity.py | 16-23 |
| build_entity_resolution | Function | backend/services/observability_analysis/entity.py | 26-60 |
| work | Function | backend/services/soc_analysis_graph/nodes_canonical.py | 65-82 |

## Execution Flows

- **work** (criticality: 0.72, depth: 5)
- **resolve_identity_endpoint** (criticality: 0.69, depth: 3)
- **run_analysis** (criticality: 0.68, depth: 3)
- **run_observability_analysis** (criticality: 0.68, depth: 3)
- **build_entity_resolution** (criticality: 0.51, depth: 1)

## Dependencies

### Outgoing

- `get` (52 edge(s))
- `lower` (13 edge(s))
- `append` (11 edge(s))
- `strip` (8 edge(s))
- `str` (8 edge(s))
- `format` (7 edge(s))
- `len` (4 edge(s))
- `info` (4 edge(s))
- `perf_counter` (3 edge(s))
- `backend/services/soc_analysis_canonical.py::build_canonical_static_context` (3 edge(s))
- `BaseModel` (2 edge(s))
- `int` (2 edge(s))
- `float` (2 edge(s))
- `join` (2 edge(s))
- `build_fallback_soc_result` (2 edge(s))

### Incoming

- `backend/services/identity_resolver.py` (8 edge(s))
- `backend/tests/test_identity_resolver.py` (4 edge(s))
- `backend/services/observability_analysis/entity.py` (3 edge(s))
- `backend/services/soc_analysis_graph/nodes_canonical.py` (3 edge(s))
- `backend/services/soc_analysis_risk.py` (3 edge(s))
- `backend/models/identity.py` (1 edge(s))
- `backend/models/observability.py` (1 edge(s))
- `backend/services/observability_analysis/runner.py::run_observability_analysis` (1 edge(s))
- `backend/api/routes/identity.py::resolve_identity_endpoint` (1 edge(s))
- `backend/services/soc_analysis/runner.py` (1 edge(s))
- `backend/services/splunk_json_store.py` (1 edge(s))
