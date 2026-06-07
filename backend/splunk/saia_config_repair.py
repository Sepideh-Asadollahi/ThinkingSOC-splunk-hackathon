"""Auto-repair Splunk AI Assistant cloud_connected_configurations on Splunk."""

from __future__ import annotations

import ast
import asyncio
import base64
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx

from config import Settings

logger = logging.getLogger(__name__)

SAIA_APP = "Splunk_AI_Assistant_Cloud"
DEFAULT_SPLUNK_HOME = "/opt/splunk"
SAIA_LOG_PATH = Path("/opt/splunk/var/log/splunk/splunk_ai_assistant.log")
TOKEN_WORKER = Path(__file__).resolve().parent / "saia_token_refresh_worker.py"

REQUIRED_KEYS = (
    "tenant_name",
    "tenant_hostname",
    "scs_region",
    "service_principal",
    "scs_token",
    "scs_token_expiry",
    "encoded_onboarding_data",
)

_repair_lock = asyncio.Lock()


def is_saia_configs_repair_error(exc_or_text: Any) -> bool:
    text = str(exc_or_text or "").lower()
    return (
        "referenced before assignment" in text and "configs" in text
    ) or "scs configs are not available properly" in text


def kv_needs_repair(current: Dict[str, Any]) -> bool:
    if not current:
        return True
    return any(not str(current.get(key) or "").strip() for key in REQUIRED_KEYS)


def _decode_jwt_payload(token: str) -> Dict[str, Any]:
    parts = (token or "").split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload.encode("ascii"))
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def _infer_tenant_hostname(tenant_name: str, scs_env: str = "splunk") -> str:
    return "{0}.api.{1}.scs.splunk.com".format(tenant_name, scs_env)


def parse_saia_log_defaults() -> Dict[str, str]:
    if not SAIA_LOG_PATH.is_file():
        return {}
    for line in SAIA_LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "maintenance_key_rotation.py" not in line or "SAIA configurations:" not in line:
            continue
        marker = "SAIA configurations: "
        idx = line.find(marker)
        if idx < 0:
            continue
        try:
            cfg = ast.literal_eval(line[idx + len(marker) :].strip())
        except Exception:
            continue
        if not isinstance(cfg, dict):
            continue
        out = {
            k: str(cfg.get(k) or "").strip()
            for k in (
                "tenant_name",
                "tenant_hostname",
                "scs_region",
                "service_principal",
                "encoded_onboarding_data",
            )
        }
        if out.get("tenant_name") and out.get("tenant_hostname"):
            return out
    return {}


def merge_saia_configs(current: Dict[str, Any]) -> Dict[str, str]:
    merged = {k: str(current.get(k) or "").strip() for k in REQUIRED_KEYS + ("last_setup_timestamp",)}
    log_defaults = parse_saia_log_defaults()

    for key in ("tenant_name", "tenant_hostname", "scs_region", "service_principal", "encoded_onboarding_data"):
        if not merged.get(key) and log_defaults.get(key):
            merged[key] = log_defaults[key]

    if not merged.get("tenant_name"):
        claims = _decode_jwt_payload(merged.get("scs_token", ""))
        tenant = str(claims.get("tenant") or "").strip()
        if tenant:
            merged["tenant_name"] = tenant

    if merged.get("tenant_name") and not merged.get("tenant_hostname"):
        merged["tenant_hostname"] = _infer_tenant_hostname(merged["tenant_name"])

    if not merged.get("service_principal"):
        claims = _decode_jwt_payload(merged.get("scs_token", ""))
        sub = str(claims.get("sub") or claims.get("cid") or "").strip()
        if sub:
            merged["service_principal"] = sub

    missing = [k for k in REQUIRED_KEYS if not merged.get(k)]
    if missing:
        raise RuntimeError(
            "SAIA configs still incomplete after inference: {0}".format(", ".join(missing))
        )
    if not merged.get("last_setup_timestamp"):
        merged["last_setup_timestamp"] = str(int(time.time()))
    return merged


def _splunk_cmd_python(settings: Settings) -> str:
    home = (getattr(settings, "splunk_home", None) or DEFAULT_SPLUNK_HOME).rstrip("/")
    return "{0}/bin/splunk".format(home)


def _refresh_token_sync(settings: Settings, session_key: str) -> str:
    splunk_bin = _splunk_cmd_python(settings)
    if not TOKEN_WORKER.is_file():
        raise RuntimeError("missing token worker: {0}".format(TOKEN_WORKER))

    proc = subprocess.run(
        [splunk_bin, "cmd", "python3", str(TOKEN_WORKER)],
        input=session_key + "\n",
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "SAIA token refresh failed (exit {0}): {1}".format(
                proc.returncode, (proc.stderr or proc.stdout or "")[:1000]
            )
        )
    for line in (proc.stdout or "").splitlines():
        if line.startswith("scs_token_expiry="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("SAIA token refresh produced no expiry")


class _SaiaKvClient:
    def __init__(self, base: str, session_key: str, verify: bool) -> None:
        self._base = base.rstrip("/") + "/"
        self._session_key = session_key
        self._verify = verify

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": "Splunk {0}".format(self._session_key)}

    async def read_kv_configs(self) -> Dict[str, Any]:
        url = urljoin(
            self._base,
            "servicesNS/nobody/{0}/storage/collections/data/cloud_connected_configurations?output_mode=json".format(
                SAIA_APP
            ),
        )
        async with httpx.AsyncClient(verify=self._verify, timeout=60.0) as client:
            r = await client.get(url, headers=self._headers())
            r.raise_for_status()
            data = r.json()
        if isinstance(data, list) and data:
            return data[0]
        return {}

    async def write_kv_entry(self, key: str, configs: Dict[str, str]) -> None:
        url = urljoin(
            self._base,
            "servicesNS/nobody/{0}/storage/collections/data/cloud_connected_configurations/{1}".format(
                SAIA_APP, key
            ),
        )
        async with httpx.AsyncClient(verify=self._verify, timeout=60.0) as client:
            r = await client.post(url, headers=self._headers(), json=configs)
            if r.status_code >= 400:
                raise RuntimeError("kv update failed HTTP {0}: {1}".format(r.status_code, r.text[:500]))

    async def write_conf_stanza(self, configs: Dict[str, str]) -> None:
        url = urljoin(
            self._base,
            "servicesNS/nobody/{0}/properties/splunkaiassistant/cloud_connected_configurations".format(
                SAIA_APP
            ),
        )
        async with httpx.AsyncClient(verify=self._verify, timeout=60.0) as client:
            r = await client.post(url, headers=self._headers(), data=configs)
            if r.status_code >= 400:
                raise RuntimeError("conf update failed HTTP {0}: {1}".format(r.status_code, r.text[:500]))

    async def reload_saia_app(self) -> None:
        url = urljoin(self._base, "services/apps/local/{0}/_reload".format(SAIA_APP))
        async with httpx.AsyncClient(verify=self._verify, timeout=120.0) as client:
            r = await client.post(url, headers=self._headers())
            if r.status_code >= 400:
                raise RuntimeError("app reload failed HTTP {0}: {1}".format(r.status_code, r.text[:500]))


async def repair_saia_cloud_configs(
    settings: Settings,
    *,
    session_key: str,
) -> bool:
    """Restore KV + conf, refresh SCS token, reload SAIA app."""
    base = settings.splunk_mgmt_url.rstrip("/")
    kv = _SaiaKvClient(base, session_key, settings.splunk_verify_ssl)
    current = await kv.read_kv_configs()
    merged = merge_saia_configs(current)

    key = str(current.get("_key") or "").strip()
    if not key:
        raise RuntimeError("cloud_connected_configurations KV entry has no _key")

    await kv.write_kv_entry(key, merged)
    expiry = await asyncio.to_thread(_refresh_token_sync, settings, session_key)
    refreshed = await kv.read_kv_configs()
    await kv.write_conf_stanza(
        {k: str(refreshed.get(k) or "") for k in REQUIRED_KEYS + ("last_setup_timestamp",)}
    )
    await kv.reload_saia_app()
    logger.info(
        "SAIA cloud_connected_configurations auto-repaired tenant=%s scs_token_expiry=%s",
        merged.get("tenant_name"),
        expiry,
    )
    return True


async def ensure_saia_cloud_configs(
    settings: Settings,
    *,
    session_key: Optional[str] = None,
    force: bool = False,
) -> bool:
    """
    Ensure SAIA KV/conf is complete. Repairs when incomplete or ``force=True``.
    Returns True when configs are usable (already OK or successfully repaired).
    """
    if not getattr(settings, "tsoc_saia_auto_repair", True):
        return False
    if not settings.splunk_username or not settings.splunk_password:
        return False

    async with _repair_lock:
        from splunk.client import SplunkRestClient

        client = SplunkRestClient(settings)
        sk = session_key or await client.login()
        kv = _SaiaKvClient(settings.splunk_mgmt_url, sk, settings.splunk_verify_ssl)
        current = await kv.read_kv_configs()
        if not force and not kv_needs_repair(current):
            return True
        try:
            return await repair_saia_cloud_configs(settings, session_key=sk)
        except Exception as e:
            logger.warning("SAIA auto-repair failed: %s", e)
            return False
