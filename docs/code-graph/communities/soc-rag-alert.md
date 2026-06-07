# soc-rag-alert

## Overview

Community of 14 nodes

- **Size**: 14 nodes
- **Cohesion**: 0.1364
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _merge_result_row | Function | backend/services/alert/alert_fields.py | 8-28 |
| build_alert_fields_for_llm | Function | backend/services/alert/alert_fields.py | 31-61 |
| _is_denied_key | Function | backend/services/soc_rag/compact_alert.py | 46-55 |
| _coerce_essential_value | Function | backend/services/soc_rag/compact_alert.py | 58-66 |
| extract_essential_fields | Function | backend/services/soc_rag/compact_alert.py | 69-87 |
| _build_summary_line | Function | backend/services/soc_rag/compact_alert.py | 90-113 |
| _build_chunk_text | Function | backend/services/soc_rag/compact_alert.py | 116-172 |
| make_doc_id | Function | backend/services/soc_rag/compact_alert.py | 175-178 |
| compact_alert_document | Function | backend/services/soc_rag/compact_alert.py | 181-224 |
| test_build_alert_fields_includes_search_name_and_all_result_keys | Test | backend/tests/test_alert_fields.py | 6-28 |
| test_build_alert_fields_merges_normalized_and_row | Test | backend/tests/test_alert_fields.py | 31-39 |
| test_build_alert_fields_uses_row_index | Test | backend/tests/test_analysis_audit.py | 37-46 |
| test_extract_essential_strips_raw_and_secrets | Test | backend/tests/test_soc_rag_compact.py | 6-17 |
| test_compact_alert_document_shape | Test | backend/tests/test_soc_rag_compact.py | 20-31 |

## Execution Flows

- **assistant_spl_suggest** (criticality: 0.78, depth: 9)
- **assemble_from_langgraph** (criticality: 0.77, depth: 8)
- **run_analysis** (criticality: 0.76, depth: 6)
- **agent_triage_endpoint** (criticality: 0.75, depth: 8)
- **run_post_ingest** (criticality: 0.75, depth: 8)
- **run_routed_analysis_endpoint** (criticality: 0.74, depth: 7)
- **review_spl_from_mcp_with_llm** (criticality: 0.73, depth: 5)
- **work** (criticality: 0.72, depth: 5)
- **run_observability_analysis** (criticality: 0.71, depth: 5)

## Dependencies

### Outgoing

- `append` (22 edge(s))
- `format` (16 edge(s))
- `get` (14 edge(s))
- `strip` (9 edge(s))
- `join` (5 edge(s))
- `len` (4 edge(s))
- `startswith` (4 edge(s))
- `isinstance` (3 edge(s))
- `items` (3 edge(s))
- `str` (3 edge(s))
- `endswith` (2 edge(s))
- `dict` (1 edge(s))
- `sorted` (1 edge(s))
- `keys` (1 edge(s))
- `lower` (1 edge(s))

### Incoming

- `backend/services/soc_rag/compact_alert.py` (7 edge(s))
- `backend/services/alert/alert_fields.py` (2 edge(s))
- `backend/tests/test_alert_fields.py` (2 edge(s))
- `backend/tests/test_soc_rag_compact.py` (2 edge(s))
- `backend/services/soc_analysis/analysis_audit.py::build_analysis_input` (1 edge(s))
- `backend/services/soc_analysis/soc_analysis_canonical.py::build_canonical_static_context` (1 edge(s))
- `backend/tests/test_analysis_audit.py` (1 edge(s))
- `endswith` (1 edge(s))
- `get` (1 edge(s))
- `len` (1 edge(s))
- `values` (1 edge(s))
