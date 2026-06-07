# ragflow-alert

## Overview

Community of 15 nodes

- **Size**: 15 nodes
- **Cohesion**: 0.1610
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| build_canonical_static_context | Function | backend/services/soc_analysis_canonical.py | 16-57 |
| _merge_result_row | Function | backend/services/alert_fields.py | 8-28 |
| build_alert_fields_for_llm | Function | backend/services/alert_fields.py | 31-61 |
| test_extract_essential_strips_raw_and_secrets | Test | backend/tests/test_ragflow_compact.py | 6-17 |
| test_compact_alert_document_shape | Test | backend/tests/test_ragflow_compact.py | 20-31 |
| test_build_alert_fields_includes_search_name_and_all_result_keys | Test | backend/tests/test_alert_fields.py | 6-28 |
| test_build_alert_fields_merges_normalized_and_row | Test | backend/tests/test_alert_fields.py | 31-39 |
| test_build_alert_fields_uses_row_index | Test | backend/tests/test_analysis_audit.py | 37-46 |
| _is_denied_key | Function | backend/services/ragflow/compact_alert.py | 46-55 |
| _coerce_essential_value | Function | backend/services/ragflow/compact_alert.py | 58-66 |
| extract_essential_fields | Function | backend/services/ragflow/compact_alert.py | 69-87 |
| _build_summary_line | Function | backend/services/ragflow/compact_alert.py | 90-113 |
| _build_chunk_text | Function | backend/services/ragflow/compact_alert.py | 116-149 |
| make_doc_id | Function | backend/services/ragflow/compact_alert.py | 152-155 |
| compact_alert_document | Function | backend/services/ragflow/compact_alert.py | 158-201 |

## Execution Flows

- **splunk_ingest** (criticality: 0.74, depth: 7)
- **run_analysis** (criticality: 0.74, depth: 5)
- **agent_triage_endpoint** (criticality: 0.73, depth: 6)
- **assistant_spl_suggest** (criticality: 0.73, depth: 5)
- **run_routed_analysis_endpoint** (criticality: 0.72, depth: 4)
- **work** (criticality: 0.72, depth: 5)
- **run_observability_analysis** (criticality: 0.71, depth: 5)

## Dependencies

### Outgoing

- `append` (16 edge(s))
- `format` (10 edge(s))
- `get` (10 edge(s))
- `strip` (9 edge(s))
- `len` (4 edge(s))
- `join` (4 edge(s))
- `isinstance` (3 edge(s))
- `str` (3 edge(s))
- `items` (2 edge(s))
- `startswith` (2 edge(s))
- `endswith` (2 edge(s))
- `dict` (1 edge(s))
- `sorted` (1 edge(s))
- `keys` (1 edge(s))
- `lower` (1 edge(s))

### Incoming

- `backend/services/ragflow/compact_alert.py` (7 edge(s))
- `backend/services/soc_analysis_graph/nodes_canonical.py::work` (3 edge(s))
- `backend/services/alert_fields.py` (2 edge(s))
- `backend/tests/test_alert_fields.py` (2 edge(s))
- `backend/tests/test_ragflow_compact.py` (2 edge(s))
- `backend/services/analysis_audit.py::build_analysis_input` (1 edge(s))
- `backend/services/soc_analysis_canonical.py` (1 edge(s))
- `backend/services/spl_mcp_review.py::review_spl_from_mcp_with_llm` (1 edge(s))
- `backend/tests/test_analysis_audit.py` (1 edge(s))
- `endswith` (1 edge(s))
- `get` (1 edge(s))
- `len` (1 edge(s))
- `values` (1 edge(s))
