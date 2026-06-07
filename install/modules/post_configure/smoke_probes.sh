#!/usr/bin/env bash
# Post-configure smoke: live Splunk REST login and MCP status API probes.

_pc_test_splunk_rest_login() {
    local env_file="$INSTALL_DIR/backend/.env"
    local venv_python="${VENV_PYTHON:-$INSTALL_DIR/backend/.venv/bin/python}"
    [[ -x "$venv_python" ]] || return 2
    "$venv_python" - "$env_file" <<'PYEOF'
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
vals = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    vals[k.strip()] = v.strip()

mgmt = vals.get("SPLUNK_MGMT_URL", "").strip()
user = vals.get("SPLUNK_USERNAME", "").strip()
password = vals.get("SPLUNK_PASSWORD", "").strip()
verify = vals.get("SPLUNK_VERIFY_SSL", "false").strip().lower() not in ("0", "false", "no")

if not user or not password:
    print("SKIP")
    raise SystemExit(0)

import httpx

url = mgmt.rstrip("/") + "/services/auth/login"
try:
    with httpx.Client(verify=verify, timeout=30.0) as client:
        r = client.post(url, data={"username": user, "password": password})
        r.raise_for_status()
        if "sessionKey" not in r.text:
            print("FAIL:no_session_key")
            raise SystemExit(1)
        print("OK")
        raise SystemExit(0)
except Exception as exc:
    print("FAIL:{0}".format(exc))
    raise SystemExit(1)
PYEOF
}

_pc_test_mcp_status_api() {
    local base="${1:-http://127.0.0.1:9876}"
    local venv_python="${VENV_PYTHON:-$INSTALL_DIR/backend/.venv/bin/python}"
    [[ -x "$venv_python" ]] || return 2
    if ! _tsoc_curl_ok "${base}/health" 2>/dev/null; then
        echo "SKIP:backend_down"
        return 2
    fi
    "$venv_python" - "$base" <<'PYEOF'
import json
import sys
import urllib.request

base = sys.argv[1].rstrip("/")
url = base + "/api/v1/mcp/status"
try:
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
except Exception as exc:
    print("FAIL:{0}".format(exc))
    raise SystemExit(1)

if not data.get("configured"):
    print("WARN:not_configured:{0}".format(data.get("message") or ""))
    raise SystemExit(2)
if data.get("connected"):
    tools = data.get("tools") or []
    print("OK:connected tools={0}".format(len(tools)))
    raise SystemExit(0)
print("WARN:not_connected:{0}".format(data.get("message") or ""))
raise SystemExit(2)
PYEOF
}
