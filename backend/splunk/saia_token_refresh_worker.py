#!/usr/bin/env python3
"""Internal worker: refresh SAIA SCS token via Splunk embedded Python."""

from __future__ import annotations

import sys

SAIA_BIN = "/opt/splunk/etc/apps/Splunk_AI_Assistant_Cloud/bin"
SAIA_LIB = "/opt/splunk/etc/apps/Splunk_AI_Assistant_Cloud/lib"
sys.path.insert(0, SAIA_BIN)
sys.path.insert(0, SAIA_LIB)

from spl_gen.cloud_connected.cc_configurations.collection import (  # noqa: E402
    CloudConnectedConfigurationsCollection,
)
from spl_gen.scs_utils import ScsUtils  # noqa: E402
from splunklib.client import connect  # noqa: E402
from splunklib.searchcommands import environment  # noqa: E402


def main() -> int:
    environment.app_root = "/opt/splunk/etc/apps/Splunk_AI_Assistant_Cloud"
    logger, _ = environment.configure_logging("saia_token_refresh_worker")
    ScsUtils.set_logger(logger)

    session_key = sys.stdin.readline().strip()
    if not session_key:
        print("session_key required on stdin", file=sys.stderr)
        return 1

    service = connect(
        host="127.0.0.1",
        port=8089,
        token=session_key,
        app="Splunk_AI_Assistant_Cloud",
        owner="nobody",
        scheme="https",
    )
    cc = CloudConnectedConfigurationsCollection(service)
    configs = cc.get()
    token, expiry = ScsUtils.refresh_scs_token_for_cmp_stack(configs, service)
    updated = dict(configs)
    updated["scs_token"] = token
    updated["scs_token_expiry"] = str(expiry)
    cc.update(updated)
    print("scs_token_expiry={0}".format(expiry))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
