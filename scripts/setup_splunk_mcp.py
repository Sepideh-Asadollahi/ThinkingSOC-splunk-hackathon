#!/usr/bin/env python3
"""
Install/enable Splunk MCP Server app, grant mcp_tool_execute, mint token into backend/.env.

Uses SPLUNK_* from backend/.env and SPLUNK_HOME for splunk CLI.
Prints OK/WARN/ERROR lines only (never secrets).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
ENV_PATH = REPO_ROOT / "backend" / ".env"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from splunk_mcp_lib import (  # noqa: E402
    MCP_APP,
    MCP_CAP_EXECUTE,
    app_enabled_via_rest,
    app_installed_on_disk,
    ensure_role_capability,
    load_env,
    mint_mcp_token,
    splunk_login,
    user_roles,
    verify_ssl_from_env,
    write_mcp_env,
)

DEFAULT_MCP_APP_URL = os.environ.get(
    "TSOC_SPLUNK_MCP_APP_URL",
    "https://splunkbase.splunk.com/app/7931/download",
)


def _run_splunk_cli(
    splunk_home: Path,
    user: str,
    password: str,
    args: list[str],
) -> tuple[int, str]:
    binary = splunk_home / "bin" / "splunk"
    if not binary.is_file():
        return 2, "splunk binary missing"
    auth = "{0}:{1}".format(user, password)
    cmd = [str(binary)] + args + ["-auth", auth]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()[:800]


def _install_mcp_app(splunk_home: Path, user: str, password: str, package: str) -> bool:
    rc, out = _run_splunk_cli(
        splunk_home,
        user,
        password,
        ["install", "app", package, "-update", "1"],
    )
    if rc == 0:
        print("OK: installed {0} from package".format(MCP_APP))
        return True
    print("WARN: splunk install app failed (rc={0}): {1}".format(rc, out))
    return False


def _enable_mcp_app(splunk_home: Path, user: str, password: str) -> bool:
    rc, out = _run_splunk_cli(
        splunk_home,
        user,
        password,
        ["enable", "app", MCP_APP],
    )
    if rc == 0:
        print("OK: enabled app {0}".format(MCP_APP))
        return True
    print("WARN: splunk enable app failed (rc={0}): {1}".format(rc, out))
    return False


def _grant_mcp_capabilities(
    base: str,
    session_key: str,
    username: str,
    verify_ssl: bool,
) -> None:
    try:
        roles = user_roles(base, session_key, username, verify_ssl)
    except Exception as exc:
        print("WARN: could not list roles for {0}: {1}".format(username, exc))
        return
    if not roles:
        print("WARN: no roles found for user {0}".format(username))
        return
    updated = 0
    for role in roles:
        try:
            if ensure_role_capability(
                base, session_key, role, MCP_CAP_EXECUTE, verify_ssl
            ):
                updated += 1
                print("OK: added {0} to role {1}".format(MCP_CAP_EXECUTE, role))
        except Exception as exc:
            print("WARN: role {0}: {1}".format(role, exc))
    if updated == 0:
        print("OK: mcp_tool_execute already present on user roles")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure Splunk MCP Server on Splunk and mint token"
    )
    parser.add_argument("--env", type=Path, default=ENV_PATH)
    parser.add_argument("--splunk-home", type=Path, default=None)
    parser.add_argument(
        "--app-package",
        default=os.environ.get("TSOC_SPLUNK_MCP_APP_PACKAGE", "").strip()
        or DEFAULT_MCP_APP_URL,
        help="splunk install app URL or local .spl/.tgz path",
    )
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--skip-mint", action="store_true")
    args = parser.parse_args()

    env = load_env(args.env)
    mgmt = env.get("SPLUNK_MGMT_URL", "https://127.0.0.1:8089").strip()
    user = env.get("SPLUNK_USERNAME", "").strip()
    password = env.get("SPLUNK_PASSWORD", "").strip()
    splunk_home = args.splunk_home or Path(
        env.get("SPLUNK_HOME", "/opt/splunk").strip() or "/opt/splunk"
    )
    verify = verify_ssl_from_env(env)

    if not user or not password:
        print("ERROR: SPLUNK_USERNAME and SPLUNK_PASSWORD required in {0}".format(args.env))
        return 1

    on_disk = app_installed_on_disk(splunk_home)
    if not on_disk and not args.skip_install:
        local_pkg = Path(args.app_package)
        if local_pkg.is_file():
            _install_mcp_app(splunk_home, user, password, str(local_pkg))
        else:
            _install_mcp_app(splunk_home, user, password, args.app_package)
        on_disk = app_installed_on_disk(splunk_home)

    if not on_disk:
        print(
            "WARN: {0} not under {1}/etc/apps/ — install Splunkbase app 7931, then re-run mint".format(
                MCP_APP, splunk_home
            )
        )
        # Still attempt login + mint if app was installed elsewhere or install failed transiently.
    else:
        print("OK: {0} present on disk".format(MCP_APP))

    if on_disk:
        _enable_mcp_app(splunk_home, user, password)

    try:
        session = splunk_login(mgmt, user, password, verify)
    except Exception as exc:
        print("ERROR: Splunk login failed: {0}".format(exc))
        return 1
    print("OK: Splunk REST login")

    if on_disk:
        enabled = app_enabled_via_rest(mgmt, session, verify)
        if enabled is False:
            print(
                "WARN: {0} still disabled via REST — restart Splunk may be required".format(
                    MCP_APP
                )
            )
        elif enabled is True:
            print("OK: {0} enabled".format(MCP_APP))

        _grant_mcp_capabilities(mgmt, session, user, verify)
    else:
        print("WARN: skipping enable/RBAC — MCP app directory missing")

    if args.skip_mint:
        print("OK: Splunk MCP setup done (mint skipped)")
        return 0

    try:
        token = mint_mcp_token(mgmt, session, user, verify)
        write_mcp_env(args.env, env, token, mgmt)
    except Exception as exc:
        print("ERROR: mint token failed: {0}".format(exc))
        print(
            "WARN: ensure {0} is enabled and user has mcp_tool_execute; Splunkbase 7931".format(
                MCP_APP
            )
        )
        return 1

    print("OK: MCP token written to {0}".format(args.env))
    return 0


if __name__ == "__main__":
    sys.exit(main())
