# investigation-timeline

## Overview

Community of 23 nodes

- **Size**: 23 nodes
- **Cohesion**: 0.1875
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _step_meta | Function | backend/services/investigation/investigation_workflow.py | 64-75 |
| _resolve_row_index | Function | backend/services/investigation/investigation_workflow.py | 78-85 |
| _same_alert_row | Function | backend/services/investigation/investigation_workflow.py | 88-106 |
| _is_timeline_pipeline_record | Function | backend/services/investigation/investigation_workflow.py | 109-116 |
| _filter_timeline_rows | Function | backend/services/investigation/investigation_workflow.py | 119-138 |
| _row_dt | Function | backend/services/investigation/investigation_workflow.py | 141-142 |
| _pick_focus_analysis_record | Function | backend/services/investigation/investigation_workflow.py | 145-156 |
| _pick_keep_id_for_type | Function | backend/services/investigation/investigation_workflow.py | 159-197 |
| _dedupe_timeline_records | Function | backend/services/investigation/investigation_workflow.py | 200-256 |
| _parse_dt | Function | backend/services/investigation/investigation_workflow.py | 259-270 |
| _timeline_detail | Function | backend/services/investigation/investigation_workflow.py | 273-326 |
| _row_to_timeline_step | Function | backend/services/investigation/investigation_workflow.py | 329-344 |
| build_investigation_timeline | Function | backend/services/investigation/investigation_workflow.py | 347-401 |
| sort_key | Function | backend/services/investigation/investigation_workflow.py | 381-386 |
| test_row_to_timeline_step_soc_analysis | Test | backend/tests/test_investigation_workflow.py | 22-37 |
| test_filter_timeline_excludes_internal_shards_and_other_rows | Test | backend/tests/test_investigation_workflow.py | 40-52 |
| test_filter_timeline_multi_row_keeps_job_ingest_and_only_this_row | Test | backend/tests/test_investigation_workflow.py | 55-71 |
| test_filter_timeline_dedupes_rerun_pipeline_steps | Test | backend/tests/test_investigation_workflow.py | 74-145 |
| test_timeline_detail_marks_legacy_dual_classification | Test | backend/tests/test_investigation_workflow.py | 148-155 |
| test_build_timeline_orders_pipeline_steps_by_rank | Test | backend/tests/test_investigation_workflow.py | 159-214 |
| test_timeline_detail_analyst_action | Test | backend/tests/test_investigation_workflow.py | 270-275 |
| test_build_timeline_not_found | Test | backend/tests/test_investigation_workflow.py | 279-287 |
| test_timeline_includes_analyst_action_step | Test | backend/tests/test_investigation_workflow.py | 334-374 |

## Execution Flows

- **get_investigation_timeline** (criticality: 0.57, depth: 5)

## Dependencies

### Outgoing

- `get` (65 edge(s))
- `str` (21 edge(s))
- `int` (12 edge(s))
- `isinstance` (10 edge(s))
- `patch` (7 edge(s))
- `add` (5 edge(s))
- `max` (5 edge(s))
- `format` (5 edge(s))
- `strip` (4 edge(s))
- `replace` (4 edge(s))
- `next` (3 edge(s))
- `append` (3 edge(s))
- `count` (3 edge(s))
- `min` (2 edge(s))
- `join` (2 edge(s))

### Incoming

- `backend/services/investigation/investigation_workflow.py` (14 edge(s))
- `backend/tests/test_investigation_workflow.py` (9 edge(s))
- `patch` (7 edge(s))
- `count` (3 edge(s))
- `len` (2 edge(s))
- `sorted` (2 edge(s))
- `get` (2 edge(s))
- `backend/api/routes/investigation.py::get_investigation_timeline` (1 edge(s))
- `next` (1 edge(s))
