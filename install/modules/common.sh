#!/usr/bin/env bash

# ── Config ───────────────────────────────────────────────────────────────────
REPO_URL="${TSOC_REPO_URL:-https://github.com/Sepideh-Asadollahi/ThinkingSOC-splunk-hackathon.git}"
INSTALL_DIR="${TSOC_INSTALL_DIR:-/opt/thinking-soc-splunk-hackathon}"
BRANCH="main"
NON_INTERACTIVE="${NON_INTERACTIVE:-false}"
# Full command output in console (apt/pip/git/npm). Set TSOC_INSTALL_QUIET=1 for minimal output.
if [[ "${TSOC_INSTALL_QUIET:-false}" == "true" ]]; then
    INSTALL_VERBOSE=false
else
    INSTALL_VERBOSE="${TSOC_INSTALL_VERBOSE:-true}"
fi
MIN_PYTHON_MINOR=11
MIN_NODE_MAJOR=20
PREFERRED_NODE_MAJOR=24
INSTALL_STATE_FILE="${TSOC_INSTALL_STATE_FILE:-}"
INSTALL_RESUME=false

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }
step()  { echo -e "\n${CYAN}${BOLD}── $* ──${NC}"; }
# Prompts go to stderr so "$(prompt_input ...)" captures only the user's answer, not the prompt text.
ask()   { echo -en "${BOLD}$*${NC} " >&2; }

# ── Install banner (centered logo + title) ───────────────────────────────────
_banner_visible_len() {
    local stripped
    stripped="$(printf '%s' "$1" | sed -r 's/\x1B\[[0-9;]*m//g')"
    printf '%s' "$stripped" | wc -m | tr -d ' '
}

center_line() {
    local line="$1"
    local cols="${2:-$(tput cols 2>/dev/null || echo 80)}"
    local len pad
    len="$(_banner_visible_len "$line")"
    pad=$(( (cols - len) / 2 ))
    (( pad < 0 )) && pad=0
    printf "%*s" "$pad" ""
    echo -e "$line"
}

print_install_banner() {
    local cols
    cols="$(tput cols 2>/dev/null || echo 80)"

    local title=(
        "  _____ _     _       _    _              ____   ___   ____ "
        " |_   _| |__ (_)_ __ | | _(_)_ __   __ _/ ___| / _ \\ / ___|"
        "   | | | '_ \\| | '_ \\| |/ / | '_ \\ / _\` \\___ \\| | | | |    "
        "   | | | | | | | | | |   <| | | | | (_| |___) | |_| | |___ "
        "   |_| |_| |_|_|_| |_|_|\\_\\_|_| |_|\\__, |____/ \\___/ \\____|"
        "                                    |___/                   "
    )

    echo ""
    center_line "${CYAN}Hackathon Edition${NC}" "$cols"
    echo ""
    echo -e "${CYAN}${BOLD}"
    local line
    for line in "${title[@]}"; do
        center_line "$line" "$cols"
    done
    echo -e "${NC}"
    center_line "${BOLD}Agentic Ops Router — Installer${NC}" "$cols"
    echo ""
}

init_install_verbose() {
    if [[ "$INSTALL_VERBOSE" == true ]]; then
        info "Verbose console logging enabled (every command printed). Set TSOC_INSTALL_QUIET=1 to hide apt/pip details."
    else
        info "Quiet install logging (summary only). Set TSOC_INSTALL_VERBOSE=1 for full command output."
    fi
}

init_install_state() {
    if [[ -z "$INSTALL_STATE_FILE" ]]; then
        INSTALL_STATE_FILE="${INSTALL_DIR}/.tsoc-install-progress"
    fi
    touch "$INSTALL_STATE_FILE" 2>/dev/null || true

    if [[ -s "$INSTALL_STATE_FILE" ]]; then
        info "Previous install progress (completed steps):"
        while IFS= read -r line; do
            [[ -n "$line" ]] && echo "  ✓ $line"
        done < "$INSTALL_STATE_FILE"
        echo ""
        if prompt_yn "Resume install (skip completed steps)?" "y"; then
            INSTALL_RESUME=true
        elif prompt_yn "Clear progress and run every step again?" "n"; then
            : > "$INSTALL_STATE_FILE"
            INSTALL_RESUME=false
            info "Progress cleared — full install"
        else
            INSTALL_RESUME=true
        fi
    else
        INSTALL_RESUME=true
    fi
}

install_step_done() {
    [[ -f "$INSTALL_STATE_FILE" ]] && grep -qxF "$1" "$INSTALL_STATE_FILE"
}

install_mark_done() {
    install_step_done "$1" && return 0
    echo "$1" >> "$INSTALL_STATE_FILE"
}

# Auto-retry then ask the user before giving up (optional step may return 1 without abort).
retry_step() {
    local label="$1"
    local hint="$2"
    shift 2
    local auto_max="${TSOC_STEP_AUTO_ATTEMPTS:-3}"
    local delay="${TSOC_STEP_RETRY_DELAY:-5}"

    while true; do
        local attempt
        for (( attempt = 1; attempt <= auto_max; attempt++ )); do
            if [[ "$attempt" -gt 1 ]]; then
                warn "${label}: auto-retry (${attempt}/${auto_max}) in ${delay}s …"
                sleep "$delay"
            fi
            if "$@"; then
                return 0
            fi
        done

        warn "${label} failed (${hint})"
        if prompt_yn "Retry '${label}' now?" "y"; then
            continue
        fi
        if prompt_yn "Stop the entire installer?" "y"; then
            err "Installation paused at: ${label}"
            err "Fix the issue, then rerun: sudo bash install.sh"
            err "Completed steps are saved in: ${INSTALL_STATE_FILE}"
            exit 1
        fi
        warn "Skipping '${label}' — later steps may fail"
        return 1
    done
}

# Required step: only retry or abort (no skip).
retry_step_strict() {
    local label="$1"
    local hint="$2"
    shift 2
    local auto_max="${TSOC_STEP_AUTO_ATTEMPTS:-3}"
    local delay="${TSOC_STEP_RETRY_DELAY:-5}"

    while true; do
        local attempt
        for (( attempt = 1; attempt <= auto_max; attempt++ )); do
            if [[ "$attempt" -gt 1 ]]; then
                warn "${label}: auto-retry (${attempt}/${auto_max}) in ${delay}s …"
                sleep "$delay"
            fi
            if "$@"; then
                return 0
            fi
        done

        warn "${label} failed (${hint})"
        if prompt_yn "Retry '${label}' now?" "y"; then
            continue
        fi
        err "Installation stopped at: ${label}"
        err "Fix the issue, then rerun: sudo bash install.sh"
        err "Completed steps are saved in: ${INSTALL_STATE_FILE}"
        exit 1
    done
}

# Run an install step; on success record progress for resume on rerun.
run_install_step() {
    local step_id="$1"
    local label="$2"
    local hint="$3"
    local strict="${4:-true}"
    shift 4

    step "$label"

    if [[ "$INSTALL_RESUME" == true ]] && install_step_done "$step_id"; then
        ok "${label} — already completed (resume)"
        return 0
    fi

    if [[ "$strict" == true ]]; then
        retry_step_strict "$label" "$hint" "$@"
    elif ! retry_step "$label" "$hint" "$@"; then
        return 1
    fi

    install_mark_done "$step_id"
}

run_cmd() {
    if [[ "$INSTALL_VERBOSE" == true ]]; then
        info "+ $*"
    fi
    "$@"
}

init_pip_network_opts() {
    PIP_NET_OPTS=(--retries 10 --timeout 120)
    if pip_trusted_host_enabled; then
        PIP_NET_OPTS+=(--trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org)
    fi
}

# TSOC_PIP_TRUSTED_HOST: auto (default) | true | false
pip_trusted_host_enabled() {
    case "${TSOC_PIP_TRUSTED_HOST:-auto}" in
        true|1|yes) return 0 ;;
        false|0|no) return 1 ;;
        *)
            [[ "${PIP_TRUSTED_HOST_ACTIVE:-false}" == true ]] \
                || [[ -f "${INSTALL_DIR}/.tsoc-pip-trusted-host" ]]
            ;;
    esac
}

probe_pypi_ssl() {
    local py="${1:-${PYTHON_CMD:-python3}}"
    "$py" -c "
import ssl
import urllib.request
try:
    urllib.request.urlopen('https://pypi.org/simple/', timeout=20)
except ssl.SSLError:
    raise SystemExit(2)
except Exception:
    raise SystemExit(1)
" 2>/dev/null
}

enable_pip_trusted_host() {
    PIP_TRUSTED_HOST_ACTIVE=true
    touch "${INSTALL_DIR}/.tsoc-pip-trusted-host" 2>/dev/null || true
}

write_venv_pip_conf() {
    local venv_dir="$1"
    mkdir -p "$venv_dir"
    cat > "${venv_dir}/pip.conf" <<'PIPEOF'
[global]
timeout = 120
retries = 10
trusted-host = pypi.org
               files.pythonhosted.org
               pypi.python.org
PIPEOF
}

configure_venv_pip_network() {
    local venv_dir="$1"
    local venv_python="${venv_dir}/bin/python"
    local probe_py="${venv_python}"
    [[ -x "$probe_py" ]] || probe_py="${PYTHON_CMD:-python3}"

    case "${TSOC_PIP_TRUSTED_HOST:-auto}" in
        true|1|yes)
            enable_pip_trusted_host
            info "pip trusted-host mode: ON (TSOC_PIP_TRUSTED_HOST)"
            ;;
        false|0|no)
            info "pip trusted-host mode: OFF (TSOC_PIP_TRUSTED_HOST=false)"
            return 0
            ;;
    esac

    if [[ -f "${INSTALL_DIR}/.tsoc-pip-trusted-host" ]]; then
        enable_pip_trusted_host
        info "pip trusted-host mode: ON (saved from a previous SSL issue on this host)"
        write_venv_pip_conf "$venv_dir"
        return 0
    fi

    info "Checking PyPI HTTPS (pypi.org) ..."
    local probe_rc=0
    probe_pypi_ssl "$probe_py" || probe_rc=$?
    if [[ "$probe_rc" -eq 0 ]]; then
        ok "PyPI HTTPS OK — standard certificate verification"
        return 0
    fi

    enable_pip_trusted_host
    write_venv_pip_conf "$venv_dir"
    if [[ "$probe_rc" -eq 2 ]]; then
        warn "PyPI SSL verification failed on this host — enabling pip trusted-host mode"
    else
        warn "Cannot reach PyPI reliably — enabling pip trusted-host mode (network/proxy)"
    fi
    info "Tip: export TSOC_PIP_TRUSTED_HOST=false to disable if you fix system CA certs later"
}

venv_pip_install() {
    local venv_python="$1"
    shift
    local venv_dir
    venv_dir="$(dirname "$(dirname "$venv_python")")"
    configure_venv_pip_network "$venv_dir"
    init_pip_network_opts

    local attempt max_attempts="${TSOC_PIP_MAX_ATTEMPTS:-3}"
    local retry_delay="${TSOC_PIP_RETRY_DELAY:-5}"
    local -a quiet_flag=()
    [[ "$INSTALL_VERBOSE" != true ]] && quiet_flag=(--quiet)

    local tried_trusted=false
    if pip_trusted_host_enabled; then
        tried_trusted=true
    fi

    for (( attempt = 1; attempt <= max_attempts; attempt++ )); do
        if [[ "$attempt" -gt 1 ]]; then
            warn "pip install retry (${attempt}/${max_attempts}) ..."
            sleep "$retry_delay"
        fi
        if [[ "$INSTALL_VERBOSE" == true ]]; then
            info "+ $venv_python -m pip install ${PIP_NET_OPTS[*]} $*"
        fi
        local err_file
        err_file="$(mktemp)"
        if "$venv_python" -m pip install "${PIP_NET_OPTS[@]}" "${quiet_flag[@]}" "$@" 2>"$err_file"; then
            rm -f "$err_file"
            return 0
        fi
        if [[ "$tried_trusted" != true ]] && grep -qiE 'ssl|certificate|SSLError|UNEXPECTED_EOF' "$err_file"; then
            warn "pip hit SSL errors — switching to trusted-host mode for PyPI"
            enable_pip_trusted_host
            write_venv_pip_conf "$venv_dir"
            init_pip_network_opts
            tried_trusted=true
            rm -f "$err_file"
            continue
        fi
        if [[ "$INSTALL_VERBOSE" == true ]] && [[ -s "$err_file" ]]; then
            cat "$err_file" >&2
        fi
        rm -f "$err_file"
    done

    err "pip install failed after ${max_attempts} attempts (PyPI SSL/network)."
    err "Fix: sudo apt install -y ca-certificates && sudo update-ca-certificates"
    err "Or force trusted-host: TSOC_PIP_TRUSTED_HOST=1 sudo bash install.sh"
    return 1
}

venv_pip_major_version() {
    local venv_python="$1"
    "$venv_python" -m pip --version 2>/dev/null | awk '{print $2}' | cut -d. -f1
}

maybe_upgrade_venv_pip() {
    local venv_python="$1"
    local pip_major
    pip_major="$(venv_pip_major_version "$venv_python")"
    if [[ "${pip_major:-0}" -ge 23 ]]; then
        ok "pip $("$venv_python" -m pip --version 2>&1 | awk '{print $2}') — OK (skipping upgrade)"
        return 0
    fi
    info "Upgrading pip (bundled version is older than 23) ..."
    venv_pip_install "$venv_python" --upgrade pip
}

list_missing_venv_packages() {
    local venv_python="$1"
    if [[ ! -f "$INSTALL_DIR/setup_tool/paths.py" ]]; then
        err "Cannot verify packages: $INSTALL_DIR/setup_tool not found"
        return 2
    fi
    (cd "$INSTALL_DIR" && "$venv_python" -c "
from setup_tool.paths import REQUIRED_IMPORTS
import importlib.util
for label, mod in REQUIRED_IMPORTS.items():
    if importlib.util.find_spec(mod) is None:
        print(label)
")
}

collect_missing_venv_packages() {
    local venv_python="$1"
    local -n _out_arr="$2"
    _out_arr=()
    local line
    while IFS= read -r line; do
        [[ -n "$line" ]] && _out_arr+=("$line")
    done < <(list_missing_venv_packages "$venv_python")
}

verify_venv_python_deps() {
    local venv_python="$1"
    local requirements="$2"
    local -a missing=()
    local offered_full_reinstall=false

    step "Verifying Python dependencies"
    info "Checking imports for packages in requirements.txt ..."

    while true; do
        collect_missing_venv_packages "$venv_python" missing

        if [[ ${#missing[@]} -eq 0 ]]; then
            ok "All required Python packages verified"
            return 0
        fi

        warn "The following packages did not install correctly (import check failed):"
        local pkg
        for pkg in "${missing[@]}"; do
            echo "  - $pkg"
        done
        echo ""

        if ! prompt_yn "Retry installing the missing packages?" "y"; then
            err "Cannot continue until all dependencies are installed."
            err "Install manually: $venv_python -m pip install ${missing[*]}"
            return 1
        fi

        info "Retrying pip install for missing packages ..."
        if ! venv_pip_install "$venv_python" "${missing[@]}"; then
            warn "pip install for missing packages failed (see errors above)"
        fi

        collect_missing_venv_packages "$venv_python" missing
        if [[ ${#missing[@]} -eq 0 ]]; then
            ok "All required Python packages verified after retry"
            return 0
        fi

        if [[ "$offered_full_reinstall" == false ]] && [[ -f "$requirements" ]]; then
            offered_full_reinstall=true
            warn "Some packages are still missing: ${missing[*]}"
            if prompt_yn "Run a full pip install -r requirements.txt again?" "y"; then
                info "Reinstalling all Python dependencies from requirements.txt ..."
                venv_pip_install "$venv_python" -r "$requirements" || true
                continue
            fi
        fi
    done
}

curl_fetch() {
    # Usage: curl_fetch <url> -o <path>  (and other curl args after URL if needed)
    local attempt max="${TSOC_STEP_AUTO_ATTEMPTS:-3}"
    local delay="${TSOC_STEP_RETRY_DELAY:-5}"
    for (( attempt = 1; attempt <= max; attempt++ )); do
        if [[ "$attempt" -gt 1 ]]; then
            warn "curl retry (${attempt}/${max}) in ${delay}s …"
            sleep "$delay"
        fi
        if [[ "$INSTALL_VERBOSE" == true ]]; then
            run_cmd curl -fL --progress-bar "$@" && return 0
        elif curl -fsSL "$@"; then
            return 0
        fi
    done
    return 1
}

apt_update_lists() {
    local attempt max="${TSOC_STEP_AUTO_ATTEMPTS:-3}"
    local delay="${TSOC_STEP_RETRY_DELAY:-5}"
    for (( attempt = 1; attempt <= max; attempt++ )); do
        [[ "$attempt" -gt 1 ]] && { warn "apt-get update retry (${attempt}/${max}) …"; sleep "$delay"; }
        if [[ "$INSTALL_VERBOSE" == true ]]; then
            run_cmd apt-get update && return 0
        elif apt-get update -qq; then
            return 0
        fi
    done
    return 1
}

apt_upgrade_all() {
    local attempt max="${TSOC_STEP_AUTO_ATTEMPTS:-3}"
    local delay="${TSOC_STEP_RETRY_DELAY:-5}"
    for (( attempt = 1; attempt <= max; attempt++ )); do
        [[ "$attempt" -gt 1 ]] && { warn "apt-get upgrade retry (${attempt}/${max}) …"; sleep "$delay"; }
        if [[ "$INSTALL_VERBOSE" == true ]]; then
            run_cmd apt-get upgrade -y && return 0
        elif apt-get upgrade -y -qq; then
            return 0
        fi
    done
    return 1
}

apt_install_packages() {
    local attempt max="${TSOC_STEP_AUTO_ATTEMPTS:-3}"
    local delay="${TSOC_STEP_RETRY_DELAY:-5}"
    for (( attempt = 1; attempt <= max; attempt++ )); do
        [[ "$attempt" -gt 1 ]] && { warn "apt-get install retry (${attempt}/${max}) …"; sleep "$delay"; }
        if [[ "$INSTALL_VERBOSE" == true ]]; then
            run_cmd apt-get install -y "$@" && return 0
        elif apt-get install -y -qq "$@"; then
            return 0
        fi
    done
    return 1
}

apt_remove_packages() {
    if [[ "$INSTALL_VERBOSE" == true ]]; then
        info "+ apt-get remove -y $*"
        apt-get remove -y "$@" || true
    else
        apt-get remove -y -qq "$@" 2>/dev/null || apt-get remove -y "$@" 2>/dev/null || true
    fi
}

need_root() {
    if [[ $EUID -ne 0 ]]; then
        err "This script must be run as root (use sudo)."
        exit 1
    fi
}

command_exists() { command -v "$1" &>/dev/null; }

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS_ID="${ID:-unknown}"
        OS_VERSION="${VERSION_ID:-}"
    else
        OS_ID="unknown"
        OS_VERSION=""
    fi
}

prompt_yn() {
    local prompt="$1" default="${2:-y}"
    if [[ "$NON_INTERACTIVE" == "true" || ! -e /dev/tty ]]; then
        [[ "$default" == "y" ]]
        return
    fi
    if [[ "$default" == "y" ]]; then
        ask "$prompt [Y/n]:"
    else
        ask "$prompt [y/N]:"
    fi
    read -r answer </dev/tty
    answer="${answer:-$default}"
    [[ "${answer,,}" == "y" || "${answer,,}" == "yes" ]]
}

prompt_input() {
    local prompt="$1" default="${2:-}"
    if [[ "$NON_INTERACTIVE" == "true" || ! -e /dev/tty ]]; then
        echo "$default"
        return 0
    fi
    ask "$prompt"
    local answer=""
    read -r answer </dev/tty
    echo "${answer:-$default}"
}

is_tsoc_repo_root() {
    local dir="$1"
    [[ -n "$dir" ]] \
        && [[ -f "$dir/setup.py" ]] \
        && [[ -f "$dir/install.sh" ]] \
        && [[ -d "$dir/install/modules" ]]
}

# When install.sh is run from a checkout outside /opt, deployment still uses the
# canonical path below (unless TSOC_INSTALL_DIR is set explicitly).
resolve_install_dir() {
    local script_dir="$1"

    if [[ -n "${TSOC_INSTALL_DIR:-}" ]]; then
        INSTALL_DIR="$(readlink -f "$TSOC_INSTALL_DIR" 2>/dev/null || echo "$TSOC_INSTALL_DIR")"
    else
        INSTALL_DIR="/opt/thinking-soc-splunk-hackathon"
    fi

    local parent
    parent="$(dirname "$INSTALL_DIR")"
    if [[ ! -d "$parent" ]]; then
        info "Creating install parent directory: $parent"
        mkdir -p "$parent"
    fi

    if is_tsoc_repo_root "$script_dir"; then
        local resolved_script
        resolved_script="$(readlink -f "$script_dir" 2>/dev/null || echo "$script_dir")"
        local resolved_install
        resolved_install="$(readlink -f "$INSTALL_DIR" 2>/dev/null || echo "$INSTALL_DIR")"
        if [[ "$resolved_script" != "$resolved_install" ]]; then
            info "Canonical install path: $INSTALL_DIR"
            warn "Installer launched from $script_dir — software will be deployed under $INSTALL_DIR"
        fi
    fi
}

validate_repo_url() {
    if [[ "$REPO_URL" == *"YOUR_ORG"* ]]; then
        warn "REPO_URL is still a placeholder."
        local suggested_url
        suggested_url="$(prompt_input "Enter Git repository URL (example: https://github.com/<org>/<repo>.git):" "")"
        if [[ -z "$suggested_url" ]]; then
            err "Repository URL is required. Set REPO_URL in install/modules/common.sh or export TSOC_REPO_URL."
            exit 1
        fi
        REPO_URL="$suggested_url"
    fi
}
