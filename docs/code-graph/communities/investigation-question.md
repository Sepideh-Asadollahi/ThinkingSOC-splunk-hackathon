# investigation-question

## Overview

Community of 12 nodes

- **Size**: 12 nodes
- **Cohesion**: 0.2360
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _field_map | Function | backend/services/investigation/investigation_question_context.py | 172-173 |
| _pick_field | Function | backend/services/investigation/investigation_question_context.py | 176-184 |
| condense_investigation_question | Function | backend/services/investigation/investigation_question_context.py | 187-204 |
| strip_time_phrases_from_question | Function | backend/services/investigation/investigation_question_context.py | 207-217 |
| question_references_alert_field | Function | backend/services/investigation/investigation_question_context.py | 220-238 |
| _target_field_from_question_hint | Function | backend/services/investigation/investigation_question_context.py | 241-253 |
| _rewrite_single_answer_with_alert | Function | backend/services/investigation/investigation_question_context.py | 256-291 |
| enrich_question_with_alert_fields | Function | backend/services/investigation/investigation_question_context.py | 294-322 |
| test_strip_time_phrases | Test | backend/tests/test_investigation_question_context.py | 16-21 |
| test_condense_splits_compound_question | Test | backend/tests/test_investigation_question_context.py | 24-28 |
| test_enrich_rewrites_parent_question | Test | backend/tests/test_investigation_question_context.py | 31-36 |
| test_enrich_keeps_existing_field_reference | Test | backend/tests/test_investigation_question_context.py | 66-71 |

## Execution Flows

- **work** (criticality: 0.74, depth: 6)
- **build_fallback_soc_result** (criticality: 0.71, depth: 5)

## Dependencies

### Outgoing

- `lower` (13 edge(s))
- `format` (7 edge(s))
- `strip` (5 edge(s))
- `sub` (5 edge(s))
- `len` (4 edge(s))
- `rstrip` (4 edge(s))
- `endswith` (3 edge(s))
- `rsplit` (2 edge(s))
- `get` (1 edge(s))
- `sorted` (1 edge(s))
- `keys` (1 edge(s))
- `find` (1 edge(s))
- `append` (1 edge(s))
- `join` (1 edge(s))
- `replace` (1 edge(s))

### Incoming

- `backend/services/investigation/investigation_question_context.py` (8 edge(s))
- `backend/tests/test_investigation_question_context.py` (4 edge(s))
- `lower` (3 edge(s))
- `endswith` (2 edge(s))
- `backend/services/investigation/investigation_question_context.py::postprocess_investigation_question_strings` (1 edge(s))
