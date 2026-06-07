# graph-pipelines-alert

## Overview

Community of 174 nodes

- **Size**: 174 nodes
- **Cohesion**: 0.2895
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| get_settings | Function | correlation/correlation_config.py | 23-24 |
| discover_attack_paths | Function | correlation/graph_api/analysis_router.py | 22-34 |
| get_operation_status | Function | correlation/graph_api/analysis_router.py | 38-45 |
| require_bearer | Function | correlation/graph_api/deps.py | 8-16 |
| require_demo_api_key | Function | correlation/graph_api/deps.py | 19-25 |
| get_topology | Function | correlation/graph_api/explorer_router.py | 14-21 |
| get_attack_tree | Function | correlation/graph_api/explorer_router.py | 25-32 |
| get_findings | Function | correlation/graph_api/findings_router.py | 22-35 |
| get_finding_graph_data | Function | correlation/graph_api/findings_router.py | 39-48 |
| patch_ticket | Function | correlation/graph_api/findings_router.py | 52-60 |
| get_finding_by_id | Function | correlation/graph_api/findings_router.py | 64-71 |
| correlate | Function | correlation/graph_api/internal_router.py | 13-17 |
| _parse_prefix_list | Function | correlation/graph_core/entity_taxonomy.py | 72-76 |
| _configured_prefix_sets | Function | correlation/graph_core/entity_taxonomy.py | 80-97 |
| entity_prefix | Function | correlation/graph_core/entity_taxonomy.py | 100-104 |
| entity_kind | Function | correlation/graph_core/entity_taxonomy.py | 107-116 |
| is_anchor_entity | Function | correlation/graph_core/entity_taxonomy.py | 119-120 |
| is_indicator_entity | Function | correlation/graph_core/entity_taxonomy.py | 123-124 |
| is_identity_anchor | Function | correlation/graph_core/entity_taxonomy.py | 127-131 |
| is_asset_anchor | Function | correlation/graph_core/entity_taxonomy.py | 134-135 |
| anchor_entities_from_identifiers | Function | correlation/graph_core/entity_taxonomy.py | 138-139 |
| anchor_entities_on_alert | Function | correlation/graph_core/entity_taxonomy.py | 142-143 |
| is_indicator_only_alert | Function | correlation/graph_core/entity_taxonomy.py | 146-150 |
| cluster_has_anchor | Function | correlation/graph_core/entity_taxonomy.py | 153-154 |
| cluster_is_indicator_only_singleton | Function | correlation/graph_core/entity_taxonomy.py | 157-161 |
| clusters_share_anchor_entities | Function | correlation/graph_core/entity_taxonomy.py | 164-174 |
| primary_anchor_display | Function | correlation/graph_core/entity_taxonomy.py | 177-184 |
| get_driver | Function | correlation/graph_core/neo4j_driver.py | 20-29 |
| close_driver | Function | correlation/graph_core/neo4j_driver.py | 32-36 |
| verify_connectivity | Function | correlation/graph_core/neo4j_driver.py | 50-57 |
| run_read_query | Function | correlation/graph_core/neo4j_driver.py | 60-70 |
| run_write_query | Function | correlation/graph_core/neo4j_driver.py | 73-83 |
| sanitize_neo4j_value | Function | correlation/graph_core/neo4j_sanitize.py | 7-20 |
| _postgres_dsn | Function | correlation/graph_core/postgres_pool.py | 16-20 |
| init_pool | Function | correlation/graph_core/postgres_pool.py | 29-38 |
| close_pool | Function | correlation/graph_core/postgres_pool.py | 41-45 |
| get_pool | Function | correlation/graph_core/postgres_pool.py | 59-62 |
| verify_connectivity | Function | correlation/graph_core/postgres_pool.py | 65-79 |
| execute_sql_file | Function | correlation/graph_core/postgres_pool.py | 86-98 |
| _label_for_node | Function | correlation/graph_crud/alert_centric.py | 80-91 |
| _merge_subgraph_rows | Function | correlation/graph_crud/alert_centric.py | 94-128 |
| _dedupe_parallel_caused_edges | Function | correlation/graph_crud/alert_centric.py | 131-161 |
| _parse_timestamp | Function | correlation/graph_crud/alert_centric.py | 164-175 |
| _alert_label | Function | correlation/graph_crud/alert_centric.py | 178-183 |
| _time_delta_seconds | Function | correlation/graph_crud/alert_centric.py | 186-191 |
| _bridge_text | Function | correlation/graph_crud/alert_centric.py | 194-212 |
| _build_caused_chain | Function | correlation/graph_crud/alert_centric.py | 215-252 |
| build_alert_centric_tree | Function | correlation/graph_crud/alert_centric.py | 255-286 |
| build_alert_centric_topology | Function | correlation/graph_crud/alert_centric.py | 289-363 |
| build_alert_centric_attack_tree | Function | correlation/graph_crud/alert_centric.py | 366-386 |

*... and 124 more members.*

## Execution Flows

- **correlate** (criticality: 0.75, depth: 4)
- **get_topology** (criticality: 0.73, depth: 6)
- **get_finding_graph_data** (criticality: 0.73, depth: 6)
- **get_attack_tree** (criticality: 0.73, depth: 6)
- **run_demo_smart_analysis** (criticality: 0.72, depth: 5)
- **get_findings** (criticality: 0.68, depth: 3)
- **patch_ticket** (criticality: 0.61, depth: 4)
- **get_finding_by_id** (criticality: 0.61, depth: 4)
- **lifespan** (criticality: 0.59, depth: 2)
- **ensure_graph_schema** (criticality: 0.58, depth: 2)
- *... and 6 more flows.*

## Dependencies

### Outgoing

- `get` (216 edge(s))
- `str` (106 edge(s))
- `len` (83 edge(s))
- `append` (55 edge(s))
- `int` (33 edge(s))
- `sorted` (27 edge(s))
- `isinstance` (23 edge(s))
- `strip` (20 edge(s))
- `set` (19 edge(s))
- `max` (17 edge(s))
- `lower` (14 edge(s))
- `list` (14 edge(s))
- `range` (13 edge(s))
- `replace` (12 edge(s))
- `BaseModel` (11 edge(s))

### Incoming

- `correlation/graph_pipelines/attack_alert_filter.py` (28 edge(s))
- `correlation/graph_pipelines/llm_stub.py` (20 edge(s))
- `correlation/graph_core/entity_taxonomy.py` (15 edge(s))
- `correlation/graph_crud/alert_centric.py` (11 edge(s))
- `correlation/graph_crud/correlation.py` (10 edge(s))
- `len` (10 edge(s))
- `correlation/tests/test_cluster_merge.py` (10 edge(s))
- `correlation/tests/test_attack_alert_filter.py` (9 edge(s))
- `correlation/graph_crud/findings.py` (8 edge(s))
- `correlation/graph_schemas/exploration.py` (8 edge(s))
- `correlation/graph_core/postgres_pool.py` (6 edge(s))
- `correlation/graph_core/neo4j_driver.py` (5 edge(s))
- `correlation/graph_pipelines/correlation_logging.py` (5 edge(s))
- `correlation/graph_api/findings_router.py` (4 edge(s))
- `correlation/graph_crud/alert_upsert.py` (4 edge(s))
