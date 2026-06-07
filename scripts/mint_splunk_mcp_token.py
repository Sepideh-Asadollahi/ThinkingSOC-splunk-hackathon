#!/usr/bin/env python3
"""
Mint Splunk MCP bearer token via REST and update backend/.env.

Uses SPLUNK_MGMT_URL, SPLUNK_USERNAME, SPLUNK_PASSWORD from backend/.env.
Prints only OK/ERROR (never the token).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
ENV_PATH = REPO_ROOT / "backend" / ".env"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from splunk_mcp_lib import (  # noqa: E402
    load_env,
    mint_mcp_token,
    splunk_login,
    verify_ssl_from_env,
    write_mcp_env,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Mint Splunk MCP token into backend/.env")
    parser.add_argument("--env", type=Path, default=ENV_PATH, help="Path to backend/.env")
    parser.add_argument("--dry-run", action="store_true", help="Mint only; do not write .env")
    args = parser.parse_args()

    env = load_env(args.env)
    mgmt = env.get("SPLUNK_MGMT_URL", "https://127.0.0.1:8089").strip()
    user = env.get("SPLUNK_USERNAME", "").strip()
    password = env.get("SPLUNK_PASSWORD", "").strip()
    verify = verify_ssl_from_env(env)

    if not user or not password:
        print("ERROR: SPLUNK_USERNAME and SPLUNK_PASSWORD must be set in {0}".format(args.env))
        return 1

    try:
        session = splunk_login(mgmt, user, password, verify)
        token = mint_mcp_token(mgmt, session, user, verify)
    except Exception as exc:
        print("ERROR: {0}".format(exc))
        return 1

    if args.dry_run:
        print("OK: token minted (dry-run, .env not updated)")
        return 0

    try:
        write_mcp_env(args.env, env, token, mgmt)
    except Exception as exc:
        print("ERROR: failed to write .env: {0}".format(exc))
        return 1

    print("OK: MCP token written to {0}".format(args.env))
    return 0


if __name__ == "__main__":
    sys.exit(main())
