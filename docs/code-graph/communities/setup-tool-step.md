# setup-tool-step

## Overview

Community of 64 nodes

- **Size**: 64 nodes
- **Cohesion**: 0.2354
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| parse_args | Function | setup_tool/cli.py | 11-33 |
| resolve_log_path | Function | setup_tool/cli.py | 36-42 |
| load_env_file | Function | setup_tool/config.py | 12-22 |
| persist_env_key | Function | setup_tool/config.py | 25-42 |
| step_config | Function | setup_tool/config.py | 45-70 |
| split_sql_statements | Function | setup_tool/database.py | 15-26 |
| _connect_postgres | Function | setup_tool/database.py | 29-32 |
| apply_schema_async | Function | setup_tool/database.py | 35-61 |
| step_database | Function | setup_tool/database.py | 64-76 |
| step_python_version | Function | setup_tool/deps.py | 16-23 |
| step_pip_bootstrap | Function | setup_tool/deps.py | 26-41 |
| verify_packages | Function | setup_tool/deps.py | 44-53 |
| step_install_requirements | Function | setup_tool/deps.py | 56-100 |
| compose_cmd | Function | setup_tool/docker.py | 35-36 |
| _is_transient_pull_error | Function | setup_tool/docker.py | 39-44 |
| pull_image_with_retry | Function | setup_tool/docker.py | 47-71 |
| pull_stack_images | Function | setup_tool/docker.py | 74-85 |
| _image_present_locally | Function | setup_tool/docker.py | 88-90 |
| ensure_stack_images | Function | setup_tool/docker.py | 93-100 |
| compose_up_with_retry | Function | setup_tool/docker.py | 103-123 |
| postgres_container_running_docker | Function | setup_tool/docker.py | 126-139 |
| try_start_existing_postgres_container | Function | setup_tool/docker.py | 142-154 |
| remove_stale_stack_containers | Function | setup_tool/docker.py | 157-167 |
| start_qdrant_docker_run | Function | setup_tool/docker.py | 170-208 |
| start_postgres_docker_run | Function | setup_tool/docker.py | 211-250 |
| start_neo4j_docker_run | Function | setup_tool/docker.py | 253-293 |
| start_stack_docker_run | Function | setup_tool/docker.py | 296-302 |
| _container_running | Function | setup_tool/docker.py | 305-318 |
| compose_stack_running | Function | setup_tool/docker.py | 321-330 |
| postgres_container_running | Function | setup_tool/docker.py | 333-336 |
| wait_postgres_ready | Function | setup_tool/docker.py | 339-369 |
| probe | Function | setup_tool/docker.py | 342-356 |
| wait_qdrant_ready | Function | setup_tool/docker.py | 372-391 |
| step_docker_postgres | Function | setup_tool/docker.py | 394-452 |
| step_project_layout | Function | setup_tool/layout.py | 9-24 |
| configure_logging | Function | setup_tool/log.py | 13-27 |
| find_compose_cmd | Function | setup_tool/prerequisites.py | 47-59 |
| _docker_client_works | Function | setup_tool/prerequisites.py | 62-73 |
| check_host_python | Function | setup_tool/prerequisites.py | 76-99 |
| check_docker | Function | setup_tool/prerequisites.py | 102-129 |
| step_prerequisites | Function | setup_tool/prerequisites.py | 132-137 |
| step_attempts | Function | setup_tool/retry_util.py | 13-14 |
| step_delay_sec | Function | setup_tool/retry_util.py | 17-18 |
| retry_sync | Function | setup_tool/retry_util.py | 21-34 |
| retry_async | Function | setup_tool/retry_util.py | 37-49 |
| _setup_stream_output | Function | setup_tool/runner.py | 22-24 |
| main | Function | setup_tool/runner.py | 27-81 |
| _print_summary | Function | setup_tool/runner.py | 84-87 |
| _finish | Function | setup_tool/runner.py | 90-102 |
| _connect_postgres | Function | setup_tool/seed.py | 15-18 |

*... and 14 more members.*

## Execution Flows

- **main** (criticality: 0.71, depth: 4)
- **postgres_container_running** (criticality: 0.45, depth: 2)

## Dependencies

### Outgoing

- `info` (74 edge(s))
- `error` (48 edge(s))
- `strip` (19 edge(s))
- `append` (14 edge(s))
- `is_file` (10 edge(s))
- `get` (10 edge(s))
- `warning` (10 edge(s))
- `add_argument` (8 edge(s))
- `sleep` (8 edge(s))
- `join` (7 edge(s))
- `run` (7 edge(s))
- `str` (7 edge(s))
- `fetchval` (7 edge(s))
- `split` (5 edge(s))
- `range` (5 edge(s))

### Incoming

- `setup_tool/docker.py` (21 edge(s))
- `setup_tool/seed.py` (7 edge(s))
- `setup_tool/prerequisites.py` (5 edge(s))
- `setup_tool/subprocess_util.py` (5 edge(s))
- `setup_tool/database.py` (4 edge(s))
- `setup_tool/deps.py` (4 edge(s))
- `setup_tool/retry_util.py` (4 edge(s))
- `setup_tool/runner.py` (4 edge(s))
- `setup_tool/config.py` (3 edge(s))
- `setup_tool/venv.py` (3 edge(s))
- `setup_tool/cli.py` (2 edge(s))
- `setup_tool/layout.py` (1 edge(s))
- `setup_tool/log.py` (1 edge(s))
- `setup.py` (1 edge(s))
