# saia-spl

## Overview

Community of 9 nodes

- **Size**: 9 nodes
- **Cohesion**: 0.2246
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _split_markdown_saia_response | Function | backend/splunk/mcp/saia/parse.py | 27-40 |
| _normalize_spl_line | Function | backend/splunk/mcp/saia/parse.py | 43-51 |
| _best_spl_from_fragment_list | Function | backend/splunk/mcp/saia/parse.py | 54-64 |
| collapse_spl_lines | Function | backend/splunk/mcp/saia/parse.py | 67-69 |
| extract_spl_from_saia_text | Function | backend/splunk/mcp/saia/parse.py | 72-124 |
| looks_like_spl_text | Function | backend/splunk/mcp/saia/parse.py | 127-135 |
| parse_saia_spl_result | Function | backend/splunk/mcp/saia/parse.py | 138-186 |
| parse_explain_text | Function | backend/splunk/mcp/saia/parse.py | 189-225 |
| test_parse_explain_text_from_mcp_results_wrapper | Test | backend/tests/test_saia_spl_parse.py | 104-119 |

## Execution Flows

- **assistant_spl_suggest** (criticality: 0.77, depth: 9)
- **assemble_from_langgraph** (criticality: 0.77, depth: 8)
- **agent_triage_endpoint** (criticality: 0.76, depth: 8)

## Dependencies

### Outgoing

- `strip` (22 edge(s))
- `isinstance` (18 edge(s))
- `get` (11 edge(s))
- `str` (6 edge(s))
- `lower` (6 edge(s))
- `startswith` (6 edge(s))
- `sub` (4 edge(s))
- `match` (4 edge(s))
- `search` (3 edge(s))
- `append` (3 edge(s))
- `start` (2 edge(s))
- `join` (2 edge(s))
- `reversed` (2 edge(s))
- `loads` (2 edge(s))
- `len` (1 edge(s))

### Incoming

- `backend/splunk/mcp/saia/parse.py` (8 edge(s))
- `backend/services/investigation/spl_predict_pipeline.py::generate_spl_via_predict` (1 edge(s))
- `backend/tests/test_saia_spl_parse.py` (1 edge(s))
