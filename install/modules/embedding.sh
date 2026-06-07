#!/usr/bin/env bash

# FastEmbed ONNX download (~220MB default bge-base / medium) — shown during install before backend start.

_tsoc_curl_ok() {
    curl -sf --noproxy '*' "$@" &>/dev/null
}

_hint_to_bytes() {
    case "$1" in
        *33MB*) echo $((33 * 1024 * 1024)) ;;
        *220MB*) echo $((220 * 1024 * 1024)) ;;
        *1.2GB*) echo $((1200 * 1024 * 1024)) ;;
        *) echo $((500 * 1024 * 1024)) ;;
    esac
}

_bytes_human() {
    local b="${1:-0}"
    if [[ "$b" -ge 1073741824 ]]; then
        printf "%.1f GB" "$(awk "BEGIN {print $b/1073741824}")"
    elif [[ "$b" -ge 1048576 ]]; then
        printf "%.0f MB" "$(awk "BEGIN {print $b/1048576}")"
    else
        printf "%.0f KB" "$(awk "BEGIN {print $b/1024}")"
    fi
}

_embedding_install_meta() {
    local venv_python="${1:?}"
    # Must run from backend/ so `import config` (backend/config.py) resolves.
    cd "$INSTALL_DIR/backend" || return 1
    "$venv_python" - <<'PY'
from config import get_settings
from services.soc_rag.embeddings import (
    _cache_has_onnx,
    _download_hint,
    fastembed_cache_dir,
    resolve_embedding_model,
)

s = get_settings()
model = resolve_embedding_model(s.tsoc_embedding_model)
cache = fastembed_cache_dir(s)
ready = _cache_has_onnx(cache, model)
hint = _download_hint(s.tsoc_embedding_model)
print(f"{cache}|{model}|{hint}|{int(ready)}")
PY
}

# Interactive embedding-model picker. Sets EMBEDDING_MODEL + EMBEDDING_DIM globals.
# Default = medium (bge-base, ~220 MB, 768-dim).
prompt_embedding_model() {
    step "Vector embedding model (SOC Chat / RAG)"
    echo "  Local FastEmbed ONNX model for semantic search. Larger = better quality, bigger download."
    echo ""
    echo -e "  ${BOLD}[1] small${NC}   bge-small   ~33 MB    384-dim   dev / slow or metered internet"
    echo -e "  ${BOLD}[2] medium${NC}  bge-base    ~220 MB   768-dim   recommended (default)"
    echo -e "  ${BOLD}[3] large${NC}   bge-large   ~1.2 GB   1024-dim  best quality"
    echo ""

    local choice
    choice="$(prompt_input "Select embedding model [1/2/3] (default 2):" "2")"
    # Defensive: if prompt text was captured (older ask on stdout), keep trailing 1/2/3 only.
    if [[ "$choice" == *"Select embedding model"* ]]; then
        choice="${choice##*: }"
        choice="${choice%% *}"
    fi
    choice="${choice//[[:space:]]/}"

    case "${choice,,}" in
        1|small|bge-small)
            EMBEDDING_MODEL="bge-small"; EMBEDDING_DIM="384" ;;
        3|large|bge-large)
            EMBEDDING_MODEL="bge-large"; EMBEDDING_DIM="1024" ;;
        2|medium|base|bge-base|"")
            EMBEDDING_MODEL="bge-base"; EMBEDDING_DIM="768" ;;
        *)
            warn "Unknown choice '${choice}' — using default medium (bge-base)"
            EMBEDDING_MODEL="bge-base"; EMBEDDING_DIM="768" ;;
    esac
    export EMBEDDING_MODEL EMBEDDING_DIM
    ok "Embedding model: ${EMBEDDING_MODEL} (${EMBEDDING_DIM}-dim) — written to new backend/.env"
    echo ""
}

_print_embedding_download_intro() {
    local model="$1"
    local size_hint="$2"
    local cache_dir="$3"
    echo ""
    echo -e "${YELLOW}${BOLD}  ⏳ Downloading vector embedding model (SOC Chat / RAG)${NC}"
    echo ""
    echo "  The backend needs a local ONNX model for semantic search (FastEmbed)."
    echo -e "  Model: ${BOLD}${model}${NC}  ·  Approx. download: ${BOLD}${size_hint}${NC}"
    echo "  Cache: ${cache_dir}"
    echo ""
    echo "  This is a one-time download. Depending on your internet speed,"
    echo "  ${size_hint} can take from a few minutes to 30+ minutes."
    echo "  Please wait — do not interrupt the installer."
    echo ""
    echo "  Need smaller/faster? Set TSOC_EMBEDDING_MODEL=bge-small (~33MB) or bge-large (~1.2GB) in"
    echo "  backend/.env (~33MB), then run: bash scripts/download-embedding-model.sh"
    echo ""
}

_monitor_embedding_download_progress() {
    local pid="$1"
    local cache_dir="$2"
    local target_bytes="$3"
    local log_file="$4"
    local width=30
    local spin='|/-\'
    local si=0
    local start_ts
    start_ts="$(date +%s)"

    # Reprint EVERY second with a spinner + elapsed clock so the line never looks
    # frozen. HuggingFace fetches small config files first, then writes the big
    # ONNX blob in large chunks, so disk size (du) can sit flat for tens of seconds.
    while kill -0 "$pid" 2>/dev/null; do
        local cur=0
        if [[ -d "$cache_dir" ]]; then
            cur="$(du -sb "$cache_dir" 2>/dev/null | awk '{print $1}')"
            cur="${cur:-0}"
        fi
        local pct=0
        if [[ "$target_bytes" -gt 0 && "$cur" -gt 0 ]]; then
            pct=$((cur * 100 / target_bytes))
            [[ "$pct" -gt 99 ]] && pct=99
        fi
        local filled=$((pct * width / 100))
        local bar empty
        bar="$(printf '%*s' "$filled" '' | tr ' ' '█')"
        empty="$(printf '%*s' "$((width - filled))" '' | tr ' ' '░')"
        local elapsed=$(( $(date +%s) - start_ts ))
        local sc="${spin:$si:1}"
        si=$(( (si + 1) % 4 ))
        printf "\r  %s [%s%s] %s / ~%s (%d%%)  %02d:%02d  " \
            "$sc" "$bar" "$empty" \
            "$(_bytes_human "$cur")" "$(_bytes_human "$target_bytes")" "$pct" \
            "$((elapsed / 60))" "$((elapsed % 60))"
        sleep 1
    done
    printf "\n"

    local rc=0
    wait "$pid" || rc=$?
    if [[ "$rc" -ne 0 ]]; then
        err "Embedding model download failed (exit ${rc}). Last log lines:"
        tail -20 "$log_file" 2>/dev/null || true
        return 1
    fi
    return 0
}

ensure_embedding_model_for_install() {
    local venv_python="${VENV_PYTHON:-$INSTALL_DIR/backend/.venv/bin/python}"
    local log_dir="${INSTALL_DIR}/logs"
    mkdir -p "$log_dir"
    local log_file="${log_dir}/embedding-download.log"

    if [[ ! -x "$venv_python" ]]; then
        err "Cannot pre-download embedding model — missing $venv_python"
        return 1
    fi

    local meta
    meta="$(_embedding_install_meta "$venv_python")" || {
        err "Could not read embedding model settings from backend/.env"
        return 1
    }

    local cache_dir model size_hint ready
    IFS='|' read -r cache_dir model size_hint ready <<<"$meta"
    local target_bytes
    target_bytes="$(_hint_to_bytes "$size_hint")"

    if [[ "$ready" == "1" ]]; then
        ok "Embedding model already cached (${model}, ${size_hint})"
        return 0
    fi

    _print_embedding_download_intro "$model" "$size_hint" "$cache_dir"

    info "Downloading… (log: ${log_file})"
    : >"$log_file"

    (
        cd "$INSTALL_DIR"
        TSOC_INSTALL_VERBOSE="${INSTALL_VERBOSE:-false}" \
            bash "$INSTALL_DIR/scripts/download-embedding-model.sh" >>"$log_file" 2>&1
    ) &
    local dl_pid=$!

    _monitor_embedding_download_progress "$dl_pid" "$cache_dir" "$target_bytes" "$log_file" || return 1

    local meta_after ready_after
    meta_after="$(_embedding_install_meta "$venv_python")"
    ready_after="${meta_after##*|}"
    if [[ "$ready_after" == "1" ]]; then
        ok "Embedding model ready (${model})"
        return 0
    fi

    warn "Download finished but cache check inconclusive — backend may download on first start"
    return 0
}

# Shown while waiting for /health when backend is still loading the model after start.
_wait_for_backend_with_embedding_notice() {
    local url="${1:-http://127.0.0.1:9876/health}"
    local label="${2:-Backend API}"
    local attempts="${3:-300}"
    local delay="${4:-2}"
    local venv_python="${VENV_PYTHON:-$INSTALL_DIR/backend/.venv/bin/python}"

    local meta cache_dir size_hint model target_bytes
    meta="$(_embedding_install_meta "$venv_python" 2>/dev/null)" || meta="|||0"
    IFS='|' read -r cache_dir model size_hint _ <<<"$meta"
    target_bytes="$(_hint_to_bytes "$size_hint")"

    echo ""
    info "Waiting for ${label} (GET /health)"
    info "Backend starts API first; embedding model (${size_hint}) may still load in background."
    info "If this takes long, watch: sudo journalctl -u tsoc-backend -f"

    local width=36
    for ((i = 1; i <= attempts; i++)); do
        if _tsoc_curl_ok "$url"; then
            printf "\n"
            ok "${label} ready (${url})"
            return 0
        fi
        local cur=0
        if [[ -d "$cache_dir" ]]; then
            cur="$(du -sb "$cache_dir" 2>/dev/null | awk '{print $1}')"
            cur="${cur:-0}"
        fi
        local pct=0
        if [[ "$target_bytes" -gt 0 && "$cur" -gt 0 ]]; then
            pct=$((cur * 100 / target_bytes))
            [[ "$pct" -gt 99 ]] && pct=99
        fi
        local filled=$((pct * width / 100))
        local bar empty
        bar="$(printf '%*s' "$filled" '' | tr ' ' '█')"
        empty="$(printf '%*s' "$((width - filled))" '' | tr ' ' '░')"
        printf "\r  [%s%s] %s / ~%s · waiting for /health (%d/%d)  " \
            "$bar" "$empty" "$(_bytes_human "$cur")" "$(_bytes_human "$target_bytes")" \
            "$i" "$attempts"
        sleep "$delay"
    done
    printf "\n"
    warn "${label} not ready yet — the installer will finish anyway; it should come up shortly in the background."
    info "  Check later:  curl -s --noproxy '*' http://127.0.0.1:9876/health"
    info "  Backend logs: tail -f ${INSTALL_DIR}/logs/backend.log   (systemd: sudo journalctl -u tsoc-backend -f)"
    return 1
}
