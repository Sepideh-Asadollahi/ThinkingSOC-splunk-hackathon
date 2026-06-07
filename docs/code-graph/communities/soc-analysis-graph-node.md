# soc-analysis-graph-node

## Overview

Community of 6 nodes

- **Size**: 6 nodes
- **Cohesion**: 0.4167
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| make_defender_node | Function | backend/services/soc_analysis_graph/nodes_llm.py | 47-57 |
| make_hunter_node | Function | backend/services/soc_analysis_graph/nodes_llm.py | 60-92 |
| make_judge_node | Function | backend/services/soc_analysis_graph/nodes_llm.py | 95-142 |
| make_framework_mapping_node | Function | backend/services/soc_analysis_graph/nodes_llm.py | 145-161 |
| make_investigation_questions_node | Function | backend/services/soc_analysis_graph/nodes_llm.py | 164-266 |
| make_llm_nodes_bundle | Function | backend/services/soc_analysis_graph/nodes_llm.py | 269-279 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `per_stage_max_tokens` (1 edge(s))

### Incoming

- `backend/services/soc_analysis_graph/nodes_llm.py` (6 edge(s))
