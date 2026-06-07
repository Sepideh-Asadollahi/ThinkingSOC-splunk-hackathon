# soc-rag-compact

## Overview

Community of 7 nodes

- **Size**: 7 nodes
- **Cohesion**: 0.0928
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _lines | Function | backend/services/soc_rag/compact_correlation.py | 15-16 |
| compact_finding_document | Function | backend/services/soc_rag/compact_correlation.py | 19-129 |
| compact_graph_alert_document | Function | backend/services/soc_rag/compact_correlation.py | 132-173 |
| compact_attack_path_document | Function | backend/services/soc_rag/compact_correlation.py | 176-205 |
| test_compact_finding_document_includes_alerts | Test | backend/tests/test_soc_rag_correlation_compact.py | 13-49 |
| test_compact_graph_alert_document | Test | backend/tests/test_soc_rag_correlation_compact.py | 52-66 |
| test_compact_attack_path_document | Test | backend/tests/test_soc_rag_correlation_compact.py | 69-77 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `format` (24 edge(s))
- `get` (22 edge(s))
- `str` (12 edge(s))
- `join` (4 edge(s))
- `isinstance` (4 edge(s))
- `RagAlertDocument` (3 edge(s))
- `append` (3 edge(s))
- `strip` (3 edge(s))
- `len` (3 edge(s))
- `enumerate` (1 edge(s))
- `dumps` (1 edge(s))
- `int` (1 edge(s))

### Incoming

- `backend/services/soc_rag/compact_correlation.py` (4 edge(s))
- `backend/tests/test_soc_rag_correlation_compact.py` (3 edge(s))
