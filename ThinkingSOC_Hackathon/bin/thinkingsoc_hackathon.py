from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import sys
import time
from collections import OrderedDict
from typing import Any, TextIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _open_results_text(path: str) -> TextIO:
    """Open Splunk alert ``results.csv`` or ``results.csv.gz`` for CSV parsing."""
    if path.lower().endswith(".gz"):
        # Splunk sendalert passes results_file=".../results.csv.gz" (gzip, not plain UTF-8).
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return open(path, newline="", encoding="utf-8")


def _read_results_file(path: str) -> list[dict[str, Any]]:
    """Load all alert result rows from Splunk's CSV results file (digest / multi-row)."""
    rows: list[dict[str, Any]] = []
    if not path or not os.path.isfile(path):
        return rows
    try:
        with _open_results_text(path) as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if isinstance(row, dict):
                    rows.append(dict(row))
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        sys.stderr.write("ERROR Failed to read results_file=%s: %s\n" % (path, exc))
    return rows


def _collect_results(settings: dict[str, Any]) -> list[dict[str, Any]]:
    """Prefer Splunk's results file (all rows); fall back to the single ``result`` dict."""
    configuration = settings.get("configuration") or {}
    results_file = (
        settings.get("results_file")
        or configuration.get("results_file")
        or settings.get("results_file_path")
    )
    if isinstance(results_file, str) and results_file.strip():
        from_file = _read_results_file(results_file.strip())
        if from_file:
            sys.stderr.write(
                "INFO Loaded %d result row(s) from results_file=%s\n"
                % (len(from_file), results_file)
            )
            return from_file
    single = settings.get("result")
    if isinstance(single, dict):
        return [single]
    return []


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
        sys.stderr.write(
            "INFO Splunk alert action stdin top_level_keys=%s\n"
            % sorted(str(k) for k in settings.keys())
        )
        configuration = settings.get("configuration", {})
        url = configuration.get("url")
        results = _collect_results(settings)
        primary = results[0] if results else settings.get("result")
        body = OrderedDict(
            sid=settings.get("sid"),
            search_name=settings.get("search_name"),
            app=settings.get("app"),
            owner=settings.get("owner"),
            results_link=settings.get("results_link"),
            result=primary,
        )
        if len(results) > 1:
            body["results"] = results
        headers = {"Content-Type": "application/json"}
        auth_token = (configuration.get("auth_token") or "").strip()
        if auth_token:
            headers["Authorization"] = "Bearer %s" % auth_token
        result = primary
        result_fp = "-"
        if isinstance(result, dict):
            canonical = json.dumps(result, sort_keys=True, default=str)
            result_fp = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
            sys.stderr.write(
                "INFO Splunk alert action invocation ts=%s sid=%s search_name=%s "
                "result_fingerprint=%s result_keys=%s _time=%s ParentImage=%s\n"
                % (
                    time.strftime("%Y-%m-%dT%H:%M:%S"),
                    settings.get("sid"),
                    settings.get("search_name"),
                    result_fp,
                    sorted(str(k) for k in result.keys()),
                    result.get("_time"),
                    result.get("ParentImage"),
                )
            )
        payload_compact = json.dumps(body, default=str)
        sys.stderr.write(
            "INFO Outgoing ThinkingSOC webhook rows=%d url=%s bytes=%d "
            "result_fingerprint=%s sid=%s search_name=%s\n"
            % (
                len(results),
                url,
                len(payload_compact),
                result_fp,
                settings.get("sid"),
                settings.get("search_name"),
            )
        )
        if not send_webhook_request(url, payload_compact, headers):
            sys.exit(2)
    except Exception as exc:
        sys.stderr.write("ERROR Unexpected error: %s\n" % exc)
        sys.exit(3)
