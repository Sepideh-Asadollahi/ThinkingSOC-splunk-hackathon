#!/usr/bin/env bash
# Post-install integration wizard — loader for install/modules/post_configure/*.sh
#
# Submodules (load order):
#   helpers.sh      prompts, env reads, Splunk path/URL
#   litellm.sh      LITELLM_MODEL picker
#   env_apply.sh    backend/.env + frontend/.env.local
#   splunk_app.sh   thinking_soc_splunk_app copy
#   mcp.sh          Splunk MCP app + RBAC + token
#   restart.sh      tsoc-backend + tsoc-frontend restart
#   smoke_probes.sh live REST / MCP API probes
#   smoke.sh        run_integration_configure_smoke
#   summary.sh      .env summary + Splunk restart reminder
#   wizard.sh       run_post_install_configure

_PC_MODULE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/post_configure" && pwd)"

_pc_require_submodule() {
    local path="$1"
    if [[ ! -f "$path" ]]; then
        echo "[ERROR] Missing post-configure module: $path" >&2
        exit 1
    fi
}

_pc_load_submodules() {
    local name path
    local -a modules=(
        helpers
        litellm
        env_apply
        splunk_app
        mcp
        restart
        smoke_probes
        smoke
        summary
        wizard
    )
    for name in "${modules[@]}"; do
        path="${_PC_MODULE_DIR}/${name}.sh"
        _pc_require_submodule "$path"
        # shellcheck disable=SC1090
        source "$path"
    done
}

_pc_load_submodules
