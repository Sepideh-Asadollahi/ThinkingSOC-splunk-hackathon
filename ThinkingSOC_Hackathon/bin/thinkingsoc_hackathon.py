from __future__ import annotations

import json
import sys
from collections import OrderedDict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def send_webhook_request(url: str, body: str, headers: dict[str, str]) -> bool:
    if not url:
        sys.stderr.write("ERROR No URL provided\n")
        return False

    sys.stderr.write(
        "INFO Sending POST request to url=%s with size=%d bytes payload\n" % (url, len(body))
    )
    try:
        if sys.version_info >= (3, 0) and isinstance(body, str):
            body = body.encode()
        req = Request(url, body, headers)
        res = urlopen(req)
        if 200 <= res.code < 300:
            sys.stderr.write("INFO Webhook receiver responded with HTTP status=%d\n" % res.code)
            return True
        sys.stderr.write("ERROR Webhook receiver responded with HTTP status=%d\n" % res.code)
        return False
    except HTTPError as exc:
        sys.stderr.write("ERROR Error sending webhook request: %s\n" % exc)
    except URLError as exc:
        sys.stderr.write("ERROR Error sending webhook request: %s\n" % exc)
    except ValueError as exc:
        sys.stderr.write("ERROR Invalid URL: %s\n" % exc)
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        sys.stderr.write("FATAL Unsupported execution mode (expected --execute flag)\n")
        sys.exit(1)

    try:
        settings = json.loads(sys.stdin.read())
        configuration = settings.get("configuration", {})
        url = configuration.get("url")
        body = OrderedDict(
            sid=settings.get("sid"),
            search_name=settings.get("search_name"),
            app=settings.get("app"),
            owner=settings.get("owner"),
            results_link=settings.get("results_link"),
            result=settings.get("result"),
        )
        headers = {"Content-Type": "application/json"}
        auth_token = (configuration.get("auth_token") or "").strip()
        if auth_token:
            headers["Authorization"] = "Bearer %s" % auth_token
        if not send_webhook_request(url, json.dumps(body), headers):
            sys.exit(2)
    except Exception as exc:
        sys.stderr.write("ERROR Unexpected error: %s\n" % exc)
        sys.exit(3)
