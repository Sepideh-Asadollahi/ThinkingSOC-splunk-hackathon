#!/usr/bin/env bash
# Post-configure: install ThinkingSOC_Hackathon_Splunk_App under SPLUNK_HOME.

_pc_install_thinking_soc_app() {
    local splunk_home="$1"
    local src="${INSTALL_DIR}/ThinkingSOC_Hackathon_Splunk_App"
    local dest="${splunk_home}/etc/apps/ThinkingSOC_Hackathon_Splunk_App"

    if [[ ! -d "$src" ]]; then
        warn "Splunk app source missing: $src"
        return 1
    fi

    info "Installing ThinkingSOC_Hackathon_Splunk_App → ${dest}"
    mkdir -p "${splunk_home}/etc/apps"
    if [[ -e "$dest" ]]; then
        if ! prompt_yn "App directory already exists — replace with repo copy?" "n"; then
            ok "Keeping existing ${dest}"
            return 0
        fi
        rm -rf "$dest"
    fi
    cp -a "$src" "$dest"
    ok "Copied ThinkingSOC_Hackathon_Splunk_App to ${dest}"

    if prompt_yn "Restart Splunk now to load the app? (may take 1–2 min)" "y"; then
        info "Running: ${splunk_home}/bin/splunk restart"
        if [[ "$INSTALL_VERBOSE" == true ]]; then
            run_cmd "${splunk_home}/bin/splunk" restart
        else
            "${splunk_home}/bin/splunk" restart
        fi
        ok "Splunk restart requested"
    else
        info "Restart Splunk later: ${splunk_home}/bin/splunk restart"
    fi
    return 0
}
