# llm-context

## Overview

Community of 5 nodes

- **Size**: 5 nodes
- **Cohesion**: 0.3103
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| context_input_char_budget | Function | backend/services/llm/llm_context_budget.py | 16-20 |
| schema_prompt_max_chars | Function | backend/services/llm/llm_context_budget.py | 29-35 |
| alert_context_max_chars | Function | backend/services/llm/llm_context_budget.py | 38-44 |
| saia_aux_context_max_chars | Function | backend/services/llm/llm_context_budget.py | 47-49 |
| test_128k_input_budget | Test | backend/tests/test_llm_context_budget.py | 12-17 |

## Execution Flows

- **saia_aux_context_max_chars** (criticality: 0.37, depth: 2)

## Dependencies

### Outgoing

- `int` (6 edge(s))
- `getattr` (3 edge(s))
- `min` (3 edge(s))
- `max` (1 edge(s))
- `model_copy` (1 edge(s))

### Incoming

- `backend/services/llm/llm_context_budget.py` (4 edge(s))
- `backend/tests/test_llm_context_budget.py` (1 edge(s))
- `model_copy` (1 edge(s))
