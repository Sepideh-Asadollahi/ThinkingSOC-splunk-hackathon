# modules-install

## Overview

Community of 37 nodes

- **Size**: 37 nodes
- **Cohesion**: 0.3920
- **Dominant Language**: bash

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| info | Function | install/modules/common.sh | 29-29 |
| ok | Function | install/modules/common.sh | 30-30 |
| warn | Function | install/modules/common.sh | 31-31 |
| err | Function | install/modules/common.sh | 32-32 |
| step | Function | install/modules/common.sh | 33-33 |
| ask | Function | install/modules/common.sh | 35-35 |
| init_install_verbose | Function | install/modules/common.sh | 81-87 |
| init_install_state | Function | install/modules/common.sh | 89-113 |
| install_step_done | Function | install/modules/common.sh | 115-117 |
| install_mark_done | Function | install/modules/common.sh | 119-122 |
| retry_step | Function | install/modules/common.sh | 125-157 |
| retry_step_strict | Function | install/modules/common.sh | 160-188 |
| run_install_step | Function | install/modules/common.sh | 191-212 |
| run_cmd | Function | install/modules/common.sh | 214-219 |
| init_pip_network_opts | Function | install/modules/common.sh | 221-226 |
| pip_trusted_host_enabled | Function | install/modules/common.sh | 229-238 |
| probe_pypi_ssl | Function | install/modules/common.sh | 240-252 |
| enable_pip_trusted_host | Function | install/modules/common.sh | 254-257 |
| write_venv_pip_conf | Function | install/modules/common.sh | 259-270 |
| configure_venv_pip_network | Function | install/modules/common.sh | 272-312 |
| venv_pip_install | Function | install/modules/common.sh | 314-365 |
| venv_pip_major_version | Function | install/modules/common.sh | 367-370 |
| maybe_upgrade_venv_pip | Function | install/modules/common.sh | 372-382 |
| list_missing_venv_packages | Function | install/modules/common.sh | 384-397 |
| collect_missing_venv_packages | Function | install/modules/common.sh | 399-407 |
| verify_venv_python_deps | Function | install/modules/common.sh | 409-460 |
| curl_fetch | Function | install/modules/common.sh | 462-478 |
| apt_update_lists | Function | install/modules/common.sh | 480-492 |
| apt_upgrade_all | Function | install/modules/common.sh | 494-506 |
| apt_install_packages | Function | install/modules/common.sh | 508-520 |
| apt_remove_packages | Function | install/modules/common.sh | 522-529 |
| need_root | Function | install/modules/common.sh | 531-536 |
| prompt_yn | Function | install/modules/common.sh | 551-565 |
| prompt_input | Function | install/modules/common.sh | 567-577 |
| is_tsoc_repo_root | Function | install/modules/common.sh | 579-585 |
| resolve_install_dir | Function | install/modules/common.sh | 589-615 |
| validate_repo_url | Function | install/modules/common.sh | 617-628 |

## Execution Flows

- **validate_repo_url** (criticality: 0.42, depth: 2)
- **verify_venv_python_deps** (criticality: 0.39, depth: 3)
- **run_install_step** (criticality: 0.38, depth: 3)
- **maybe_upgrade_venv_pip** (criticality: 0.38, depth: 3)
- **init_install_state** (criticality: 0.37, depth: 2)
- **curl_fetch** (criticality: 0.37, depth: 2)
- **apt_update_lists** (criticality: 0.37, depth: 2)
- **apt_upgrade_all** (criticality: 0.37, depth: 2)

## Dependencies

### Outgoing

- `return` (32 edge(s))
- `echo` (16 edge(s))
- `true` (8 edge(s))
- `sleep` (7 edge(s))
- `apt-get` (5 edge(s))
- `read` (4 edge(s))
- `"$venv_python"` (4 edge(s))
- `exit` (4 edge(s))
- `shift` (4 edge(s))
- `continue` (4 edge(s))
- `readlink` (3 edge(s))
- `"$@"` (3 edge(s))
- `rm` (3 edge(s))
- `touch` (2 edge(s))
- `grep` (2 edge(s))

### Incoming

- `install/modules/common.sh` (37 edge(s))
