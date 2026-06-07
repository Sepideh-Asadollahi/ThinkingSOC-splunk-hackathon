# services-user

## Overview

Community of 21 nodes

- **Size**: 21 nodes
- **Cohesion**: 0.3986
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _norm_str | Function | backend/services/enrichment_resolver.py | 33-36 |
| _rows_matching_exact | Function | backend/services/enrichment_resolver.py | 39-56 |
| _pick_asset_row | Function | backend/services/enrichment_resolver.py | 59-69 |
| _pick_user_row | Function | backend/services/enrichment_resolver.py | 72-75 |
| _match_assets | Function | backend/services/enrichment_resolver.py | 78-95 |
| _match_users | Function | backend/services/enrichment_resolver.py | 98-120 |
| _asset_criticality_rank | Function | backend/services/enrichment_resolver.py | 123-127 |
| _user_risk_rank | Function | backend/services/enrichment_resolver.py | 130-137 |
| _pick_relationship_for_user | Function | backend/services/enrichment_resolver.py | 140-153 |
| _pick_relationship_for_asset | Function | backend/services/enrichment_resolver.py | 156-169 |
| _apply_relationships | Function | backend/services/enrichment_resolver.py | 172-209 |
| enrich_from_inventory | Function | backend/services/enrichment_resolver.py | 212-256 |
| _sample_tables | Function | backend/tests/test_enrichment_resolver.py | 8-24 |
| test_resolve_host_and_user | Test | backend/tests/test_enrichment_resolver.py | 27-32 |
| test_no_match_note | Test | backend/tests/test_enrichment_resolver.py | 35-41 |
| test_highest_criticality_pick | Test | backend/tests/test_enrichment_resolver.py | 44-52 |
| test_relationship_links_user_when_only_asset_matched | Test | backend/tests/test_enrichment_resolver.py | 55-61 |
| test_relationship_links_asset_when_only_user_matched | Test | backend/tests/test_enrichment_resolver.py | 64-69 |
| test_relationship_does_not_override_both_sides_already_matched | Test | backend/tests/test_enrichment_resolver.py | 72-77 |
| test_relationship_picks_highest_criticality_asset_for_user | Test | backend/tests/test_enrichment_resolver.py | 80-92 |
| test_relationship_picks_highest_risk_user_for_asset | Test | backend/tests/test_enrichment_resolver.py | 95-107 |

## Execution Flows

- **run_analysis** (criticality: 0.74, depth: 5)
- **run_observability_analysis** (criticality: 0.71, depth: 5)
- **enrich_endpoint** (criticality: 0.70, depth: 4)

## Dependencies

### Outgoing

- `get` (20 edge(s))
- `lower` (8 edge(s))
- `append` (7 edge(s))
- `format` (4 edge(s))
- `len` (4 edge(s))
- `max` (2 edge(s))
- `backend/models/enrichment.py::EnrichmentResult` (2 edge(s))
- `set` (1 edge(s))
- `add` (1 edge(s))
- `strip` (1 edge(s))
- `str` (1 edge(s))
- `keys` (1 edge(s))
- `int` (1 edge(s))
- `extend` (1 edge(s))
- `join` (1 edge(s))

### Incoming

- `backend/services/enrichment_resolver.py` (12 edge(s))
- `backend/tests/test_enrichment_resolver.py` (9 edge(s))
- `lower` (2 edge(s))
- `backend/tests/test_soc_analysis_risk.py::test_build_risk_context_after_relationship_link` (1 edge(s))
- `backend/services/soc_analysis/runner.py::run_analysis` (1 edge(s))
- `backend/services/observability_analysis/runner.py::run_observability_analysis` (1 edge(s))
- `backend/api/routes/inventory.py::enrich_endpoint` (1 edge(s))
