"""Shared Splunk REST helpers for MCP install/mint scripts."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

MCP_APP = "Splunk_MCP_Server"
MCP_CAP_EXECUTE = "mcp_tool_execute"
MCP_CAP_ADMIN = "mcp_tool_admin"

MCP_ENV_DEFAULTS: dict[str, str] = {
    "TSOC_MCP_ENABLED": "true",
    "SPLUNK_MCP_VERIFY_SSL": "false",
    "TSOC_SPL_USE_REST_PREDICT": "true",
    "TSOC_MCP_SAIA_OPTIMIZE_SPL": "true",
    "TSOC_MCP_SAIA_EXPLAIN_SPL": "true",
    "TSOC_SPL_LLM_REVIEW": "true",
    "TSOC_EXECUTE_INVESTIGATION_SPL": "true",
}


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip()
    return out


def verify_ssl_from_env(env: dict[str, str]) -> bool:
    return env.get("SPLUNK_VERIFY_SSL", "false").strip().lower() not in ("0", "false", "no")


def parse_session_key(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    for elem in root.iter():
        if elem.tag.endswith("sessionKey") and elem.text:
            return elem.text.strip()
    raise ValueError("sessionKey not found in Splunk login response")


def splunk_login(base: str, user: str, password: str, verify_ssl: bool) -> str:
    url = urljoin(base.rstrip("/") + "/", "services/auth/login")
    with httpx.Client(verify=verify_ssl, timeout=60.0) as client:
        r = client.post(url, data={"username": user, "password": password})
        r.raise_for_status()
        return parse_session_key(r.text)


def auth_headers(session_key: str) -> dict[str, str]:
    return {"Authorization": "Splunk {0}".format(session_key)}


def mint_mcp_token(
    base: str,
    session_key: str,
    username: str,
    verify_ssl: bool,
) -> str:
    from urllib.parse import urlencode

    qs = urlencode({"username": username, "output_mode": "json"})
    path = "servicesNS/nobody/{0}/mcp_token?{1}".format(MCP_APP, qs)
    url = urljoin(base.rstrip("/") + "/", path)
    with httpx.Client(verify=verify_ssl, timeout=120.0) as client:
        r = client.get(url, headers=auth_headers(session_key))
        if r.status_code >= 400:
            raise RuntimeError("mcp_token HTTP {0}: {1}".format(r.status_code, r.text[:500]))
        data = r.json()
    token = data.get("token")
    if not token and isinstance(data.get("entry"), list) and data["entry"]:
        content = data["entry"][0].get("content") or {}
        token = content.get("token")
    if not token:
        raise RuntimeError("mcp_token response missing token field")
    return str(token).strip()


def upsert_env_line(lines: list[str], key: str, value: str) -> None:
    pattern = re.compile(r"^\s*{0}\s*=".format(re.escape(key)))
    new_line = "{0}={1}".format(key, value)
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = new_line
            return
    if lines and lines[-1].strip():
        lines.append("")
    lines.append(new_line)


def write_mcp_env(path: Path, env: dict[str, str], token: str, mgmt_url: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    mcp_url = mgmt_url.rstrip("/") + "/services/mcp"
    updates = dict(MCP_ENV_DEFAULTS)
    updates["TSOC_MCP_ENABLED"] = "true"
    updates["SPLUNK_MCP_URL"] = mcp_url
    updates["SPLUNK_MCP_TOKEN"] = token
    for key, val in updates.items():
        upsert_env_line(lines, key, val)
    if "SPLUNK_VERIFY_SSL" not in env and not any(
        re.match(r"^\s*SPLUNK_VERIFY_SSL\s*=", ln) for ln in lines
    ):
        upsert_env_line(lines, "SPLUNK_VERIFY_SSL", "false")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _first_entry_content(data: dict[str, Any]) -> dict[str, Any]:
    entries = data.get("entry") or []
    if not entries:
        return {}
    return entries[0].get("content") or {}


def app_installed_on_disk(splunk_home: Path) -> bool:
    return (splunk_home / "etc" / "apps" / MCP_APP).is_dir()


def app_enabled_via_rest(
    base: str,
    session_key: str,
    verify_ssl: bool,
) -> bool | None:
    """Return True/False if app record exists; None if endpoint unavailable."""
    url = urljoin(base.rstrip("/") + "/", "services/apps/local/{0}".format(MCP_APP))
    params = {"output_mode": "json"}
    with httpx.Client(verify=verify_ssl, timeout=60.0) as client:
        r = client.get(url, headers=auth_headers(session_key), params=params)
        if r.status_code == 404:
            return False
        if r.status_code >= 400:
            return None
        data = r.json()
    content = _first_entry_content(data)
    disabled = content.get("disabled")
    if disabled is None:
        return True
    return str(disabled).lower() in ("0", "false", "no")


def user_roles(
    base: str,
    session_key: str,
    username: str,
    verify_ssl: bool,
) -> list[str]:
    url = urljoin(
        base.rstrip("/") + "/",
        "services/authentication/users/{0}".format(username),
    )
    with httpx.Client(verify=verify_ssl, timeout=60.0) as client:
        r = client.get(
            url,
            headers=auth_headers(session_key),
            params={"output_mode": "json"},
        )
        if r.status_code >= 400:
            raise RuntimeError("user lookup HTTP {0}".format(r.status_code))
        data = r.json()
    content = _first_entry_content(data)
    roles = content.get("roles") or []
    if isinstance(roles, str):
        roles = [roles]
    return [str(x).strip() for x in roles if str(x).strip()]


def role_capabilities(
    base: str,
    session_key: str,
    role: str,
    verify_ssl: bool,
) -> list[str]:
    url = urljoin(
        base.rstrip("/") + "/",
        "services/authorization/roles/{0}".format(role),
    )
    with httpx.Client(verify=verify_ssl, timeout=60.0) as client:
        r = client.get(
            url,
            headers=auth_headers(session_key),
            params={"output_mode": "json"},
        )
        if r.status_code >= 400:
            raise RuntimeError("role {0} HTTP {1}".format(role, r.status_code))
        data = r.json()
    content = _first_entry_content(data)
    caps = content.get("capabilities") or []
    if isinstance(caps, str):
        caps = [caps]
    return [str(c).strip() for c in caps if str(c).strip()]


def ensure_role_capability(
    base: str,
    session_key: str,
    role: str,
    capability: str,
    verify_ssl: bool,
) -> bool:
    """Add capability to role if missing. Returns True if role was updated."""
    caps = role_capabilities(base, session_key, role, verify_ssl)
    if capability in caps:
        return False
    caps.append(capability)
    url = urljoin(
        base.rstrip("/") + "/",
        "services/authorization/roles/{0}".format(role),
    )
    form: list[tuple[str, str]] = [("name", role)]
    for cap in caps:
        form.append(("capabilities", cap))
    with httpx.Client(verify=verify_ssl, timeout=60.0) as client:
        r = client.post(url, headers=auth_headers(session_key), data=form)
        if r.status_code >= 400:
            raise RuntimeError(
                "update role {0} HTTP {1}: {2}".format(role, r.status_code, r.text[:300])
            )
    return True
