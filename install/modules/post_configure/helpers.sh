#!/usr/bin/env bash
# Post-configure: prompts, env file reads, Splunk path/URL helpers.

prompt_secret() {
    local prompt="$1"
    if [[ "$NON_INTERACTIVE" == "true" || ! -e /dev/tty ]]; then
        echo ""
        return 0
    fi
    ask "$prompt"
    local answer=""
    read -rs answer </dev/tty
    echo ""
    echo "$answer"
}

_pc_env_get() {
    local file="$1" key="$2" val=""
    if [[ -f "$file" ]]; then
        val="$(grep -E "^[[:space:]]*${key}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' || true)"
    fi
    echo "$val"
    return 0
}

_pc_default_splunk_home() {
    if [[ -n "${SPLUNK_HOME:-}" && -x "${SPLUNK_HOME}/bin/splunk" ]]; then
        echo "$SPLUNK_HOME"
        return 0
    fi
    if [[ -x /opt/splunk/bin/splunk ]]; then
        echo "/opt/splunk"
        return 0
    fi
    echo "/opt/splunk"
}

_pc_validate_splunk_home() {
    local home="$1"
    [[ -n "$home" && -x "${home}/bin/splunk" ]]
}

_pc_parse_mgmt_url() {
    # Sets _PC_SPLUNK_HOST and _PC_SPLUNK_PORT from SPLUNK_MGMT_URL-style URL.
    local url="$1"
    local hostport="${url#*://}"
    hostport="${hostport%%/*}"
    _PC_SPLUNK_HOST="${hostport%%:*}"
    if [[ "$hostport" == *:* ]]; then
        _PC_SPLUNK_PORT="${hostport##*:}"
    else
        _PC_SPLUNK_PORT="8089"
    fi
}
