# soc-analysis-graph-soc

## Overview

Community of 2 nodes

- **Size**: 2 nodes
- **Cohesion**: 0.0278
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| build_soc_analysis_graph | Function | backend/services/soc_analysis_graph/graph.py | 27-54 |
| run_soc_analysis_langgraph | Function | backend/services/soc_analysis_graph/graph.py | 57-77 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `add_node` (9 edge(s))
- `add_edge` (9 edge(s))
- `get` (2 edge(s))
- `info` (2 edge(s))
- `perf_counter` (2 edge(s))
- `make_llm_nodes_bundle` (1 edge(s))
- `StateGraph` (1 edge(s))
- `make_prepare_node` (1 edge(s))
- `make_risk_engine_node` (1 edge(s))
- `make_virustotal_node` (1 edge(s))
- `make_root_cause_spl_node` (1 edge(s))
- `set_entry_point` (1 edge(s))
- `compile` (1 edge(s))
- `ainvoke` (1 edge(s))

### Incoming

- `backend/services/soc_analysis_graph/graph.py` (2 edge(s))
