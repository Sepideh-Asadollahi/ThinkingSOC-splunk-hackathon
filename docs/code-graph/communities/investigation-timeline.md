# investigation-timeline

## Overview

Community of 21 nodes

- **Size**: 21 nodes
- **Cohesion**: 0.1875
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _step_meta | Function | backend/services/investigation/investigation_workflow.py | 64-75 |
| _resolve_row_index | Function | backend/services/investigation/investigation_workflow.py | 78-85 |
| _is_timeline_pipeline_record | Function | backend/services/investigation/investigation_workflow.py | 88-95 |
| _filter_timeline_rows | Function | backend/services/investigation/investigation_workflow.py | 98-119 |
| _row_dt | Function | backend/services/investigation/investigation_workflow.py | 122-123 |
| _pick_focus_analysis_record | Function | backend/services/investigation/investigation_workflow.py | 126-137 |
| _pick_keep_id_for_type | Function | backend/services/investigation/investigation_workflow.py | 140-178 |
| _dedupe_timeline_records | Function | backend/services/investigation/investigation_workflow.py | 181-237 |
| _parse_dt | Function | backend/services/investigation/investigation_workflow.py | 240-251 |
| _timeline_detail | Function | backend/services/investigation/investigation_workflow.py | 254-307 |
| _row_to_timeline_step | Function | backend/services/investigation/investigation_workflow.py | 310-325 |
| build_investigation_timeline | Function | backend/services/investigation/investigation_workflow.py | 328-378 |
| sort_key | Function | backend/services/investigation/investigation_workflow.py | 358-363 |
| test_row_to_timeline_step_soc_analysis | Test | backend/tests/test_investigation_workflow.py | 22-37 |
| test_filter_timeline_excludes_internal_shards_and_other_rows | Test | backend/tests/test_investigation_workflow.py | 40-52 |
| test_filter_timeline_dedupes_rerun_pipeline_steps | Test | backend/tests/test_investigation_workflow.py | 55-126 |
| test_timeline_detail_marks_legacy_dual_classification | Test | backend/tests/test_investigation_workflow.py | 129-136 |
| test_build_timeline_orders_pipeline_steps_by_rank | Test | backend/tests/test_investigation_workflow.py | 140-195 |
| test_timeline_detail_analyst_action | Test | backend/tests/test_investigation_workflow.py | 251-256 |
| test_build_timeline_not_found | Test | backend/tests/test_investigation_workflow.py | 260-268 |
| test_timeline_includes_analyst_action_step | Test | backend/tests/test_investigation_workflow.py | 315-355 |

## Execution Flows

- **get_investigation_timeline** (criticality: 0.57, depth: 5)

## Dependencies

### Outgoing

- `get` (63 edge(s))
- `str` (19 edge(s))
- `int` (12 edge(s))
- `isinstance` (10 edge(s))
- `patch` (7 edge(s))
- `add` (5 edge(s))
- `max` (5 edge(s))
- `format` (5 edge(s))
- `replace` (4 edge(s))
- `next` (3 edge(s))
- `append` (3 edge(s))
- `count` (3 edge(s))
- `min` (2 edge(s))
- `strip` (2 edge(s))
- `join` (2 edge(s))

### Incoming

- `backend/services/investigation/investigation_workflow.py` (13 edge(s))
- `backend/tests/test_investigation_workflow.py` (8 edge(s))
- `patch` (7 edge(s))
- `count` (3 edge(s))
- `len` (2 edge(s))
- `get` (2 edge(s))
- `backend/api/routes/investigation.py::get_investigation_timeline` (1 edge(s))
- `next` (1 edge(s))
