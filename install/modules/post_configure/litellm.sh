#!/usr/bin/env bash
# Post-configure: LiteLLM model, API key, and API base (always prompted).

_pc_litellm_model_default() {
    local env_file="$INSTALL_DIR/backend/.env"
    local model
    model="$(_pc_env_get "$env_file" LITELLM_MODEL)"
    if [[ -z "$model" ]]; then
        model="$(_pc_env_get "$INSTALL_DIR/backend/.env.example" LITELLM_MODEL)"
    fi
    echo "${model:-gpt-4o-mini}"
}

_pc_litellm_api_base_default() {
    _pc_env_get "$INSTALL_DIR/backend/.env" LITELLM_API_BASE
}

_pc_normalize_prompt_choice() {
    local raw="$1"
    if [[ "$raw" == *"Choose model"* || "$raw" == *"LITELLM"* ]]; then
        raw="${raw##*: }"
        raw="${raw%% *}"
    fi
    echo "${raw//[[:space:]]/}"
}

_pc_prompt_litellm_model() {
    local current choice custom
    current="$(_pc_litellm_model_default)"

    echo ""
    echo -e "  ${BOLD}LITELLM_MODEL${NC} (current in .env: ${current})"
    echo "    [1] Keep current (${current})"
    echo "    [2] gpt-4o-mini (OpenAI)"
    echo "    [3] gpt-4o (OpenAI)"
    echo "    [4] anthropic/claude-3-5-haiku-20241022"
    echo "    [5] anthropic/claude-3-5-sonnet-20241022"
    echo "    [6] Enter custom model id"
    echo ""
    choice="$(prompt_input "Choose model [1]:" "1")"
    choice="$(_pc_normalize_prompt_choice "${choice:-1}")"

    case "$choice" in
        1)
            PC_LITELLM_MODEL="$current"
            ;;
        2)
            PC_LITELLM_MODEL="gpt-4o-mini"
            ;;
        3)
            PC_LITELLM_MODEL="gpt-4o"
            ;;
        4)
            PC_LITELLM_MODEL="anthropic/claude-3-5-haiku-20241022"
            ;;
        5)
            PC_LITELLM_MODEL="anthropic/claude-3-5-sonnet-20241022"
            ;;
        6)
            custom="$(prompt_input "Custom LITELLM_MODEL id:" "$current")"
            PC_LITELLM_MODEL="${custom:-$current}"
            ;;
        *)
            warn "Unknown model choice '${choice}' — using ${current}"
            PC_LITELLM_MODEL="$current"
            ;;
    esac
    ok "LITELLM_MODEL=${PC_LITELLM_MODEL}"
}

# Always ask model + API key (required) + API base (optional URL).
_pc_prompt_litellm_config() {
    PC_LITELLM_KEY=""
    PC_LITELLM_API_BASE=""

    _pc_prompt_litellm_model

    echo ""
    local llm_key=""
    while [[ -z "$llm_key" ]]; do
        llm_key="$(prompt_secret "LITELLM_API_KEY (required — OpenAI/Anthropic/etc.):")"
        if [[ -z "$llm_key" ]]; then
            warn "LITELLM_API_KEY cannot be empty when LLM is enabled"
        fi
    done
    PC_LITELLM_KEY="$llm_key"
    ok "LITELLM_API_KEY will be saved to backend/.env"

    echo ""
    local base_default
    base_default="$(_pc_litellm_api_base_default)"
    PC_LITELLM_API_BASE="$(prompt_input "LITELLM_API_BASE (optional proxy URL, Enter to skip):" "$base_default")"
    if [[ -n "$PC_LITELLM_API_BASE" ]]; then
        ok "LITELLM_API_BASE=${PC_LITELLM_API_BASE}"
    else
        info "LITELLM_API_BASE left empty (LiteLLM uses provider default endpoints)"
    fi
}
