#!/usr/bin/env python3
"""
Standalone SAIA path debugger — compares UI chat vs MCP/generatespl vs direct cloud API.

Does not import ThinkingSOC Lite backend. Only httpx + stdlib.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx", file=sys.stderr)
    sys.exit(1)

SAIA_APP = "Splunk_AI_Assistant_Cloud"
MCP_APP = "Splunk_MCP_Server"
PROMPT = "index=_internal | head 3"


@dataclass
class ProbeResult:
    name: str
    status: str  # PASS, FAIL, SKIP
    detail: str
    url: str = ""
    http_status: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = val.strip()


def _parse_session_key(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    for elem in root.iter():
        if elem.tag.endswith("sessionKey") and elem.text:
            return elem.text.strip()
    raise ValueError("sessionKey not found")


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.environ.get(name, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


@dataclass
class SplunkSession:
    base: str
    session_key: str
    verify_ssl: bool
    username: str

    def auth_header(self) -> Dict[str, str]:
        return {"Authorization": "Splunk {0}".format(self.session_key)}

    def ns_url(self, app: str, path: str) -> str:
        """servicesNS/nobody/{app}/{path}"""
        p = "servicesNS/nobody/{0}/{1}".format(app, path.lstrip("/"))
        return urljoin(self.base.rstrip("/") + "/", p)


class SaiaPathDebugger:
    def __init__(self, session: SplunkSession, mcp_token: Optional[str] = None) -> None:
        self.session = session
        self.mcp_token = (mcp_token or "").strip()
        self.results: List[ProbeResult] = []
        self.tenant_hostname: Optional[str] = None
        self.tenant_name: Optional[str] = None
        self.scs_token: Optional[str] = None

    def _record(self, result: ProbeResult) -> None:
        self.results.append(result)
        mark = {"PASS": "✓", "FAIL": "✗", "SKIP": "○"}.get(result.status, "?")
        line = "{0} {1}".format(mark, result.name)
        if result.http_status is not None:
            line += " HTTP {0}".format(result.http_status)
        if result.url:
            line += " → {0}".format(result.url)
        print(line)
        if result.detail:
            for part in result.detail.splitlines()[:8]:
                print("    ", part)
        print()

    def probe_login(self) -> None:
        self._record(
            ProbeResult(
                "splunk_login",
                "PASS",
                "user={0}".format(self.session.username),
                url=self.session.base + "services/auth/login",
            )
        )

    def probe_saia_config(self) -> None:
        url = self.session.ns_url(SAIA_APP, "config?output_mode=json")
        try:
            with httpx.Client(verify=self.session.verify_ssl, timeout=60.0) as client:
                r = client.get(url, headers=self.session.auth_header())
            if r.status_code != 200:
                self._record(
                    ProbeResult(
                        "saia_config",
                        "FAIL",
                        r.text[:500],
                        url=url,
                        http_status=r.status_code,
                    )
                )
                return
            data = r.json()
            entry = (data.get("entry") or [{}])[0]
            content = entry.get("content") or data
            self.tenant_hostname = content.get("tenant_hostname") or content.get("tenantHostname")
            self.tenant_name = content.get("tenant_name") or content.get("tenant")
            self._record(
                ProbeResult(
                    "saia_config",
                    "PASS",
                    "tenant={0} hostname={1}".format(self.tenant_name, self.tenant_hostname),
                    url=url,
                    http_status=200,
                    extra={"keys": sorted(content.keys())[:20]},
                )
            )
        except Exception as exc:
            self._record(ProbeResult("saia_config", "FAIL", str(exc), url=url))

    def probe_cloud_connected_kv(self) -> None:
        url = self.session.ns_url(
            SAIA_APP,
            "storage/collections/data/cloud_connected_configurations/config?output_mode=json",
        )
        try:
            with httpx.Client(verify=self.session.verify_ssl, timeout=60.0) as client:
                r = client.get(url, headers=self.session.auth_header())
            if r.status_code != 200:
                self._record(
                    ProbeResult(
                        "cloud_connected_kv",
                        "SKIP",
                        "KV not readable HTTP {0}: {1}".format(r.status_code, r.text[:200]),
                        url=url,
                        http_status=r.status_code,
                    )
                )
                return
            data = r.json()
            fields = (data.get("entry") or [{}])[0].get("fields") or data
            self.tenant_hostname = self.tenant_hostname or fields.get("tenant_hostname")
            self.tenant_name = self.tenant_name or fields.get("tenant_name")
            token = (fields.get("scs_token") or "").strip()
            self.scs_token = token or None
            masked = "(empty)" if not token else token[:8] + "…" + token[-4:] if len(token) > 16 else "***"
            self._record(
                ProbeResult(
                    "cloud_connected_kv",
                    "PASS",
                    "tenant={0} hostname={1} scs_token={2}".format(
                        self.tenant_name, self.tenant_hostname, masked
                    ),
                    url=url,
                    http_status=200,
                )
            )
        except Exception as exc:
            self._record(ProbeResult("cloud_connected_kv", "SKIP", str(exc), url=url))

    def probe_generatespl_mcp_path(self) -> None:
        """Same REST handler MCP uses: oneshot_generation_handler → V2 spl/write when V2_FLAG=True."""
        url = self.session.ns_url(SAIA_APP, "generatespl?output_mode=json")
        body = {
            "prompt": PROMPT,
            "spl_only": True,
        }
        headers = {
            **self.session.auth_header(),
            "Content-Type": "application/json",
            "source-app-id": "saia-debug-probe",
        }
        try:
            with httpx.Client(verify=self.session.verify_ssl, timeout=120.0) as client:
                r = client.post(url, headers=headers, json=body)
            text = r.text[:1200]
            if r.status_code == 200:
                self._record(
                    ProbeResult(
                        "splunk_generatespl (MCP path, SAIA v2)",
                        "PASS",
                        text[:400],
                        url=url,
                        http_status=200,
                    )
                )
                return
            # Extract cloud URL from error if present
            cloud_hint = ""
            if "saia-api" in text:
                for token in text.replace("\\", "").split():
                    if "scs.splunk.com" in token or "saia-api" in token:
                        cloud_hint = token.strip('"{},')
                        break
            self._record(
                ProbeResult(
                    "splunk_generatespl (MCP path, SAIA v2)",
                    "FAIL",
                    text + ("\ncloud_url_hint: " + cloud_hint if cloud_hint else ""),
                    url=url,
                    http_status=r.status_code,
                    extra={"note": "Splunk_AI_Assistant_Cloud base_rest.V2_FLAG=True → saia-api-v2/v2alpha1/spl/write"},
                ),
            )
        except Exception as exc:
            self._record(
                ProbeResult("splunk_generatespl (MCP path, SAIA v2)", "FAIL", str(exc), url=url)
            )

    def probe_predict_ui_path(self) -> None:
        """UI chat entry — async job; v1 search flow (not v2 spl/write)."""
        url = self.session.ns_url(SAIA_APP, "predict?output_mode=json")
        chat_id = str(uuid.uuid4())
        body = {
            "prompt": PROMPT,
            "classification": 0,
            "chat_id": chat_id,
        }
        headers = {
            **self.session.auth_header(),
            "Content-Type": "application/json",
            "Source-App-ID": "saia-debug-probe",
        }
        try:
            with httpx.Client(verify=self.session.verify_ssl, timeout=120.0) as client:
                r = client.post(url, headers=headers, json=body)
            text = r.text[:800]
            ok = r.status_code == 200 and ("job_id" in text or "response_id" in text)
            self._record(
                ProbeResult(
                    "splunk_predict (UI chat path, SAIA v1 async)",
                    "PASS" if ok else "FAIL",
                    text,
                    url=url,
                    http_status=r.status_code,
                    extra={"note": "generation_handler uses SaiaApi v1 search — not spl/write v2"},
                ),
            )
        except Exception as exc:
            self._record(ProbeResult("splunk_predict (UI chat path)", "FAIL", str(exc), url=url))

    def probe_mcp_jsonrpc(self) -> None:
        if not self.mcp_token:
            self._record(
                ProbeResult(
                    "mcp_saia_generate_spl (JSON-RPC)",
                    "SKIP",
                    "Set SPLUNK_MCP_TOKEN to test MCP layer",
                )
            )
            return
        mcp_url = os.environ.get(
            "SPLUNK_MCP_URL", self.session.base.rstrip("/") + "/services/mcp"
        )
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "saia_generate_spl",
                "arguments": {"prompt": PROMPT, "spl_only": True},
            },
        }
        headers = {
            "Authorization": "Bearer {0}".format(self.mcp_token),
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        try:
            with httpx.Client(verify=self.session.verify_ssl, timeout=120.0) as client:
                init = {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "saia-debug", "version": "1.0"},
                    },
                }
                client.post(mcp_url, headers=headers, json=init)
                client.post(
                    mcp_url,
                    headers=headers,
                    json={"jsonrpc": "2.0", "id": 99, "method": "notifications/initialized"},
                )
                r = client.post(mcp_url, headers=headers, json=payload)
            data = r.json() if r.text.strip() else {}
            err = (data.get("result") or {}).get("isError") or data.get("error")
            if r.status_code == 200 and not err:
                self._record(
                    ProbeResult(
                        "mcp_saia_generate_spl (JSON-RPC)",
                        "PASS",
                        json.dumps(data)[:400],
                        url=mcp_url,
                        http_status=200,
                    )
                )
            else:
                detail = json.dumps(data)[:1200]
                self._record(
                    ProbeResult(
                        "mcp_saia_generate_spl (JSON-RPC)",
                        "FAIL",
                        detail,
                        url=mcp_url,
                        http_status=r.status_code,
                        extra={"note": "MCP calls generatespl internally — same v2 cloud path"},
                    ),
                )
        except Exception as exc:
            self._record(
                ProbeResult("mcp_saia_generate_spl (JSON-RPC)", "FAIL", str(exc), url=mcp_url)
            )

    def probe_cloud_v1_metadata(self) -> None:
        if not self.tenant_hostname or not self.tenant_name or not self.scs_token:
            self._record(
                ProbeResult(
                    "cloud_v1_metadata (direct)",
                    "SKIP",
                    "Need tenant_hostname, tenant_name, scs_token from probes above",
                )
            )
            return
        host = self.tenant_hostname.rstrip("/")
        if not host.startswith("http"):
            host = "https://" + host
        url = "{0}/{1}/saia-api/v1alpha1/api/metadata".format(host, self.tenant_name)
        headers = {"Authorization": "Bearer {0}".format(self.scs_token), "X-Request-ID": str(uuid.uuid4())}
        try:
            with httpx.Client(verify=self.session.verify_ssl, timeout=60.0) as client:
                r = client.get(url, headers=headers)
            self._record(
                ProbeResult(
                    "cloud_v1_metadata (direct) — UI stack uses v1",
                    "PASS" if r.status_code == 200 else "FAIL",
                    r.text[:400],
                    url=url,
                    http_status=r.status_code,
                ),
            )
        except Exception as exc:
            self._record(ProbeResult("cloud_v1_metadata (direct)", "FAIL", str(exc), url=url))

    def probe_cloud_v2_spl_write(self) -> None:
        if not self.tenant_hostname or not self.tenant_name or not self.scs_token:
            self._record(
                ProbeResult(
                    "cloud_v2_spl_write (direct)",
                    "SKIP",
                    "Need tenant_hostname, tenant_name, scs_token",
                )
            )
            return
        host = self.tenant_hostname.rstrip("/")
        if not host.startswith("http"):
            host = "https://" + host
        url = "{0}/{1}/saia-api-v2/v2alpha1/spl/write".format(host, self.tenant_name)
        headers = {
            "Authorization": "Bearer {0}".format(self.scs_token),
            "Content-Type": "application/json",
            "X-Request-ID": str(uuid.uuid4()),
        }
        body = {
            "user_prompt": PROMPT,
            "chat_id": "debug",
            "chat_history": [],
            "source_app_id": "saia-debug",
            "app_version": "0.0.0",
            "locale": "en-US",
            "request_id": str(uuid.uuid4()),
            "log_to_telemetry": False,
        }
        try:
            with httpx.Client(verify=self.session.verify_ssl, timeout=90.0) as client:
                r = client.post(url, headers=headers, json=body)
            self._record(
                ProbeResult(
                    "cloud_v2_spl_write (direct) — MCP/generatespl uses this",
                    "PASS" if r.status_code in (200, 201) else "FAIL",
                    r.text[:500],
                    url=url,
                    http_status=r.status_code,
                ),
            )
        except Exception as exc:
            self._record(ProbeResult("cloud_v2_spl_write (direct)", "FAIL", str(exc), url=url))

    def print_diagnosis(self) -> None:
        print("=" * 72)
        print("DIAGNOSIS (read this)")
        print("=" * 72)
        v1 = next((r for r in self.results if "v1_metadata" in r.name), None)
        v2_gen = next((r for r in self.results if "generatespl" in r.name), None)
        v2_cloud = next((r for r in self.results if "v2_spl_write" in r.name), None)
        ui = next((r for r in self.results if "predict" in r.name), None)

        print(
            """
Splunk AI Assistant uses TWO different cloud API generations:

  • UI chat  → REST /predict → SaiaApi v1 (saia-api/v1alpha1, e.g. api/search)
  • MCP tool → REST /generatespl → SAIAApiV2 (saia-api-v2/v2alpha1/spl/write)
               Splunk app hardcodes V2_FLAG = True in base_rest.py

Your license can work for v1 (chat) while v2 endpoint returns 404 if the
tenant/stack was not provisioned for SAIA API v2 yet.
"""
        )
        if ui and ui.status == "PASS":
            print("• UI path (/predict): OK — chat can enqueue v1 jobs.")
        if v2_gen and v2_gen.status == "FAIL" and "404" in v2_gen.detail:
            print("• MCP path (/generatespl): FAIL with 404 on saia-api-v2 …/spl/write")
            print("  → This is NOT a ThinkingSOC Lite bug; Splunk MCP → v2 cloud route missing.")
        if v1 and v1.status == "PASS" and v2_cloud and v2_cloud.status == "FAIL":
            print("• Direct cloud test: v1 metadata OK, v2 spl/write FAIL")
            print("  → Fix on Splunk side: enable SAIA v2 / Agent Mode for tenant, or")
            print("    ask Splunk support why v2alpha1/spl/write is not deployed on your stack.")
        if v1 and v1.status == "PASS" and v2_cloud and v2_cloud.status == "PASS":
            print("• Both v1 and v2 cloud OK — investigate generatespl handler / headers next.")
        print()
        print("Splunk-side references:")
        print("  Splunk_AI_Assistant_Cloud/bin/base_rest.py          → V2_FLAG = True")
        print("  Splunk_AI_Assistant_Cloud/bin/generation_handler.py → v1 SaiaApi for /predict")
        print("  Splunk_AI_Assistant_Cloud/bin/oneshot_generation_handler.py → v2 spl_write for /generatespl")
        print("  Splunk_MCP_Server/default/builtin_tools.json        → MCP → POST .../generatespl")
        print("=" * 72)

    def run_all(self) -> int:
        print("SAIA path debugger — tenant/stack probe\n")
        self.probe_login()
        self.probe_saia_config()
        self.probe_cloud_connected_kv()
        self.probe_predict_ui_path()
        self.probe_generatespl_mcp_path()
        self.probe_mcp_jsonrpc()
        self.probe_cloud_v1_metadata()
        self.probe_cloud_v2_spl_write()
        self.print_diagnosis()
        fails = sum(1 for r in self.results if r.status == "FAIL")
        return 1 if fails else 0


def splunk_login(
    base: str, username: str, password: str, verify_ssl: bool
) -> SplunkSession:
    url = urljoin(base.rstrip("/") + "/", "services/auth/login")
    with httpx.Client(verify=verify_ssl, timeout=60.0) as client:
        r = client.post(url, data={"username": username, "password": password})
        r.raise_for_status()
        key = _parse_session_key(r.text)
    return SplunkSession(base=base, session_key=key, verify_ssl=verify_ssl, username=username)


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug SAIA UI vs MCP API paths")
    parser.add_argument(
        "--env",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "backend" / ".env",
        help="Optional .env file (default: repo backend/.env)",
    )
    args = parser.parse_args()
    if args.env.is_file():
        _load_env_file(args.env)

    base = os.environ.get("SPLUNK_MGMT_URL", "https://127.0.0.1:8089").strip()
    user = os.environ.get("SPLUNK_USERNAME", "").strip()
    password = os.environ.get("SPLUNK_PASSWORD", "").strip()
    verify = _bool_env("SPLUNK_VERIFY_SSL", default=False)
    mcp_token = os.environ.get("SPLUNK_MCP_TOKEN", "").strip()

    if not user or not password:
        print("Set SPLUNK_USERNAME and SPLUNK_PASSWORD", file=sys.stderr)
        return 1

    try:
        session = splunk_login(base, user, password, verify)
    except Exception as exc:
        print("Splunk login failed:", exc, file=sys.stderr)
        return 1

    return SaiaPathDebugger(session, mcp_token=mcp_token or None).run_all()


if __name__ == "__main__":
    sys.exit(main())
