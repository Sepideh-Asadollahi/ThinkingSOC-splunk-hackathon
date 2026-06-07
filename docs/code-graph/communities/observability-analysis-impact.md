# observability-analysis-impact

## Overview

Community of 4 nodes

- **Size**: 4 nodes
- **Cohesion**: 0.2581
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| ImpactContext | Class | backend/models/observability.py | 21-26 |
| _to_float | Function | backend/services/observability_analysis/impact.py | 10-16 |
| _severity_score | Function | backend/services/observability_analysis/impact.py | 19-20 |
| build_impact_context | Function | backend/services/observability_analysis/impact.py | 23-72 |

## Execution Flows

- **build_impact_context** (criticality: 0.43, depth: 1)

## Dependencies

### Outgoing

- `get` (8 edge(s))
- `lower` (3 edge(s))
- `strip` (3 edge(s))
- `str` (3 edge(s))
- `BaseModel` (1 edge(s))
- `float` (1 edge(s))

### Incoming

- `backend/services/observability_analysis/impact.py` (3 edge(s))
- `backend/models/observability.py` (1 edge(s))
