# soc-analysis-graph-user

## Overview

Community of 6 nodes

- **Size**: 6 nodes
- **Cohesion**: 0.1923
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| system_context_user_block | Function | backend/services/soc_analysis_graph/messages.py | 11-16 |
| defender_user_message | Function | backend/services/soc_analysis_graph/messages.py | 19-24 |
| hunter_user_message | Function | backend/services/soc_analysis_graph/messages.py | 27-44 |
| judge_user_message | Function | backend/services/soc_analysis_graph/messages.py | 47-69 |
| investigation_questions_user_message | Function | backend/services/soc_analysis_graph/messages.py | 72-111 |
| framework_mapping_user_message | Function | backend/services/soc_analysis_graph/messages.py | 114-132 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `dumps` (9 edge(s))
- `format_hunter_mcp_for_prompt` (2 edge(s))
- `format` (1 edge(s))
- `max` (1 edge(s))
- `int` (1 edge(s))
- `format_judge_mcp_for_prompt` (1 edge(s))

### Incoming

- `backend/services/soc_analysis_graph/messages.py` (6 edge(s))
