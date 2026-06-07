#!/usr/bin/env python3
"""
Test a Splunk webhook JSON file the same way the hackathon frontend talks to the backend.

Default output: timestamped logs + a RESULT SUMMARY block at the end
(including which alert fields were used for LLM analysis).
Use -v/--verbose for full JSON payloads in logs.

Modes:
  console (default) — POST /analysis/route then GET /storage/events
  webhook           — POST /alerts/splunk-ingest
  full              — webhook ingest + poll storage events

Examples:
  python3 scripts/test_splunk_webhook.py scripts/samples/splunk-webhook-example.json
  # console mode auto-uses result rows from JSON (--offline) when Splunk is not running
  python3 scripts/test_splunk_webhook.py --live-splunk attack.json   # force Splunk REST on :8089
  python3 scripts/test_splunk_webhook.py -v --mode webhook attack.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ScriptError(Exception):
    """Expected failure with a user-facing explanation (no traceback by default)."""

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_ENV = REPO_ROOT / "frontend" / ".env.local"
BACKEND_ENV = BACKEND_DIR / ".env"

log = logging.getLogger("test_splunk_webhook")

_NORMALIZED_KEYS = (
    "_time",
    "host",
    "src",
    "dest",
    "user",
    "severity",
    "signature",
    "signature_id",
    "service",
    "status_code",
    "latency_ms",
    "error_rate",
    "cpu",
    "memory",
    "disk",
)

# PostgreSQL tsoc_record_type values written by persist_soc_investigation_phases + route.
INVESTIGATION_DB_TYPES: Tuple[str, ...] = (
    "soc_analysis_audit",
    "soc_investigation_raw_alert",
    "soc_investigation_alert_fields",
    "soc_investigation_defender",
    "soc_investigation_hunter",
    "soc_investigation_judge",
    "soc_investigation_questions",
    "soc_investigation_framework",
    "soc_investigation_identity",
    "soc_investigation_risk",
    "soc_investigation_summary",
    "soc_investigation_root_cause_spl",
    "soc_analysis",
    "agentic_ops_analysis",
)

_PHASE_LABELS: Dict[str, str] = {
    "raw_alert": "Raw alert (SID, search_name, row_index, normalized, result_row)",
    "alert_fields": "Alert context (each Splunk result field + search_name)",
    "defender": "Defender — triage narrative",
    "hunter": "Hunter — hunt narrative & SPL ideas",
    "judge": "Judge — verdict & priority",
    "investigation_questions": "Investigation questions",
    "framework_mapping": "MITRE / framework mapping",
    "identity_resolution": "Identity resolution",
    "risk_context": "Risk context",
    "summary": "Executive summary",
    "root_cause_spl": "Root-cause SPL (analyst-run)",
}


@dataclass
class RunSummary:
    ok: bool = True
    mode: str = ""
    json_file: str = ""
    dry_run: bool = False
    offline: bool = False
    base_url: str = ""
    sid: Optional[str] = None
    search_name: Optional[str] = None
    steps: List[str] = field(default_factory=list)
    http: Dict[str, int] = field(default_factory=dict)
    route_track: Optional[str] = None
    route_pipeline: Optional[str] = None
    judge_verdict: Optional[str] = None
    ingest_status: Optional[str] = None
    stored_events: int = 0
    db_phase_records: int = 0
    row_index: int = 0
    splunk_results_row_count: int = 0
    analysis_fields: Dict[str, Any] = field(default_factory=dict)
    analysis_fields_source: Optional[str] = None
    raw_alert: Dict[str, Any] = field(default_factory=dict)
    analysis_input: Dict[str, Any] = field(default_factory=dict)
    analysis_output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: float = field(default_factory=time.monotonic)

    def step(self, msg: str) -> None:
        self.steps.append(msg)
        log.info(msg)

    def fail(self, msg: str) -> None:
        self.ok = False
        self.error = msg
        log.error(msg)

    def duration_sec(self) -> float:
        return time.monotonic() - self.started_at


def _explain_exception(exc: BaseException, *, verbose: bool) -> str:
    """Turn common failures into actionable messages."""
    if isinstance(exc, ScriptError):
        return str(exc)
    if isinstance(exc, KeyboardInterrupt):
        return "Stopped by user (Ctrl+C)"
    if isinstance(exc, json.JSONDecodeError):
        return "Invalid JSON at line {0} column {1}: {2}".format(
            exc.lineno, exc.colno, exc.msg
        )
    if isinstance(exc, FileNotFoundError):
        return "File not found: {0}".format(exc.filename or exc)
    if isinstance(exc, PermissionError):
        return "Permission denied: {0}".format(exc)
    if isinstance(exc, urllib.error.HTTPError):
        return "HTTP {0} from server".format(exc.code)
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, socket.timeout):
            return "Connection timed out — backend or Splunk may be slow or down"
        if isinstance(reason, ConnectionRefusedError):
            return (
                "Connection refused — backend not listening. "
                "Start: cd backend && .venv/bin/python run.py"
            )
        return "Network error: {0}".format(reason)
    if isinstance(exc, TimeoutError):
        return "Request timed out"
    if isinstance(exc, OSError) and exc.errno is not None:
        return "OS error ({0}): {1}".format(exc.errno, exc.strerror or exc)
    if verbose:
        return "".join(traceback.format_exception_only(type(exc), exc)).strip()
    return "{0}: {1}".format(type(exc).__name__, exc)


def setup_logging(*, verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )


def build_alert_fields_for_summary(
    *,
    search_name: Optional[str],
    normalized: Dict[str, Any],
    splunk_results: List[Dict[str, Any]],
    row_index: int = 0,
) -> Dict[str, Any]:
    """Mirror backend ``build_alert_fields_for_llm`` (search_name + merged result row)."""
    merged: Dict[str, Any] = dict(normalized or {})
    row: Optional[Dict[str, Any]] = None
    if splunk_results:
        idx = row_index if 0 <= row_index < len(splunk_results) else 0
        if isinstance(splunk_results[idx], dict):
            row = splunk_results[idx]
    if row:
        for key, val in row.items():
            sk = str(key)
            if sk.startswith("__mv_"):
                continue
            if val is not None:
                merged[sk] = val
    fields: Dict[str, Any] = {}
    sn = (search_name or "").strip()
    if sn:
        fields["search_name"] = sn
    fields["row_index"] = row_index
    for key in sorted(merged.keys()):
        if key == "search_name":
            continue
        val = merged[key]
        if val is None:
            continue
        if isinstance(val, str) and not val.strip():
            continue
        fields[key] = val
    return fields


def extract_audit_from_db(by_type: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Load soc_analysis_audit row (input + output + raw_alert)."""
    rows = by_type.get("soc_analysis_audit") or []
    if not rows:
        return {}
    payload = rows[0].get("payload") if isinstance(rows[0].get("payload"), dict) else rows[0]
    return payload if isinstance(payload, dict) else {}


def extract_alert_fields_from_db(by_type: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Prefer persisted ``soc_investigation_alert_fields`` from PostgreSQL."""
    rows = by_type.get("soc_investigation_alert_fields") or []
    if not rows:
        return {}
    row = rows[0]
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else row
    if not isinstance(payload, dict):
        return {}
    content = _payload_content(payload)
    return content if isinstance(content, dict) else {}


def resolve_analysis_fields(
    handoff: Dict[str, Any],
    by_type: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    *,
    row_index: int = 0,
) -> Tuple[Dict[str, Any], str]:
    """Return (fields, source label) for RESULT SUMMARY."""
    if by_type:
        audit = extract_audit_from_db(by_type)
        inp = audit.get("analysis_input") if isinstance(audit.get("analysis_input"), dict) else {}
        af = inp.get("alert_fields") if isinstance(inp.get("alert_fields"), dict) else {}
        if af:
            return af, "PostgreSQL (soc_analysis_audit.analysis_input)"
        from_db = extract_alert_fields_from_db(by_type)
        if from_db:
            return from_db, "PostgreSQL (soc_investigation_alert_fields)"
    rows = list(handoff.get("results") or [])
    from_handoff = build_alert_fields_for_summary(
        search_name=handoff.get("search_name"),
        normalized=handoff.get("normalized") or {},
        splunk_results=rows,
        row_index=row_index,
    )
    if from_handoff:
        label = "webhook JSON (normalized + first result row)"
        if not rows and handoff.get("normalized"):
            label = "webhook JSON (normalized only)"
        elif rows and not handoff.get("normalized"):
            label = "webhook JSON (first result row)"
        return from_handoff, label
    return {}, "none"


def _format_analysis_fields_block(fields: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    for key in sorted(fields.keys()):
        val = fields[key]
        if isinstance(val, (dict, list)):
            text = json.dumps(val, ensure_ascii=False, default=str)
        else:
            text = str(val)
        if len(text) > 120:
            text = text[:117] + "..."
        lines.append("    {0}: {1}".format(key, text))
    return lines


def _log_json(label: str, data: Any, *, verbose: bool) -> None:
    if verbose:
        log.debug("%s\n%s", label, json.dumps(data, indent=2, ensure_ascii=False, default=str))
    elif isinstance(data, dict):
        keys = ", ".join(sorted(data.keys())[:12])
        extra = " …" if len(data) > 12 else ""
        log.info("%s (%d keys: %s%s)", label, len(data), keys, extra)
    else:
        log.info("%s: %s", label, data)


def print_result_summary(summary: RunSummary) -> None:
    """Final human-readable outcome (always printed to stdout)."""
    lines = [
        "",
        "=" * 72,
        "RESULT SUMMARY",
        "=" * 72,
        "Status:       {0}".format("SUCCESS" if summary.ok else "FAILED"),
        "Mode:         {0}{1}".format(
            summary.mode,
            " (offline)" if summary.offline else "",
        ),
        "File:         {0}".format(summary.json_file),
    ]
    if summary.dry_run:
        lines.append("Dry run:      yes (no HTTP calls)")
    if summary.base_url:
        lines.append("Backend:      {0}".format(summary.base_url))
    if summary.sid:
        lines.append("SID:          {0}".format(summary.sid))
    if summary.search_name:
        lines.append("Search name:  {0}".format(summary.search_name))
    lines.append("Row index:    {0}".format(summary.row_index))
    if summary.splunk_results_row_count:
        lines.append("Result rows:  {0}".format(summary.splunk_results_row_count))
    if summary.http:
        lines.append("HTTP:")
        for name, code in summary.http.items():
            lines.append("  {0} → {1}".format(name, code))
    if summary.ingest_status:
        lines.append("Ingest:       {0}".format(summary.ingest_status))
    if summary.route_track:
        lines.append("Route track:  {0}".format(summary.route_track))
    if summary.route_pipeline:
        lines.append("Pipeline:     {0}".format(summary.route_pipeline))
    if summary.judge_verdict:
        lines.append("Judge:        {0}".format(summary.judge_verdict))
    lines.append("")
    lines.append("--- Analysis audit (what was sent / returned) ---")
    if summary.raw_alert:
        lines.append("Raw alert:")
        lines.extend(_format_analysis_fields_block(summary.raw_alert))
    else:
        lines.append("Raw alert:    (not loaded)")
    if summary.analysis_input:
        inp = summary.analysis_input
        af = inp.get("alert_fields") if isinstance(inp.get("alert_fields"), dict) else inp
        lines.append("Sent to analysis (analysis_input):")
        lines.extend(_format_analysis_fields_block(af if isinstance(af, dict) else inp))
    if summary.analysis_output:
        lines.append("Analysis output:")
        lines.extend(_format_analysis_fields_block(summary.analysis_output))
    elif summary.ok and summary.http.get("POST /analysis/route") == 200:
        lines.append("Analysis output: (no security pipeline or empty)")
    if summary.analysis_fields:
        src = summary.analysis_fields_source or "unknown"
        lines.append(
            "Analysis fields ({0} keys, source: {1}):".format(
                len(summary.analysis_fields), src
            )
        )
        lines.extend(_format_analysis_fields_block(summary.analysis_fields))
    elif summary.analysis_fields_source:
        lines.append("Analysis fields: (none — {0})".format(summary.analysis_fields_source))
    lines.append("Stored events:{0}".format(summary.stored_events))
    if summary.db_phase_records:
        lines.append("DB phases:    {0} investigation record(s) loaded".format(summary.db_phase_records))
    if summary.error:
        lines.append("Error:        {0}".format(summary.error))
    if not summary.ok and summary.http.get("POST /analysis/route") == 502:
        lines.append(
            "Hint:         Splunk REST on 127.0.0.1:8089 unreachable — re-run with captured JSON rows"
        )
        lines.append("              (default auto --offline) or start Splunk / fix backend/.env")
    lines.append("Duration:     {0:.1f}s".format(summary.duration_sec()))
    if summary.steps:
        lines.append("Steps:")
        for s in summary.steps:
            lines.append("  • {0}".format(s))
    lines.append("=" * 72)
    print("\n".join(lines), flush=True)


def _load_dotenv(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def _resolve_config() -> Tuple[str, Optional[str]]:
    backend_env = _load_dotenv(BACKEND_ENV)
    frontend_env = _load_dotenv(FRONTEND_ENV)
    host = backend_env.get("TSOC_HTTP_HOST", "127.0.0.1")
    port = backend_env.get("TSOC_HTTP_PORT", "9876")
    base = os.environ.get("TSOC_BASE_URL") or frontend_env.get("TSOC_BACKEND_URL")
    if not base:
        base = "http://{0}:{1}".format(host, port)
    base = base.rstrip("/")
    token = (
        os.environ.get("TSOC_INGEST_TOKEN")
        or frontend_env.get("TSOC_INGEST_TOKEN")
        or backend_env.get("TSOC_INGEST_TOKEN")
        or None
    )
    if token is not None and not str(token).strip():
        token = None
    return base, token


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ScriptError("Cannot read {0}: {1}".format(path, e)) from e
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ScriptError(
            "Invalid JSON in {0} (line {1}, column {2}): {3}".format(
                path.name, e.lineno, e.colno, e.msg
            )
        ) from e
    if not isinstance(data, dict):
        raise ScriptError("JSON root must be an object {{...}}, not {0}".format(type(data).__name__))
    return data


def _first_non_empty(*values: Any) -> Optional[str]:
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")


def _row_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    one = payload.get("result")
    if isinstance(one, dict):
        return one
    many = payload.get("results")
    if isinstance(many, list) and many and isinstance(many[0], dict):
        return many[0]
    return {}


def _build_normalized(payload: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    existing = payload.get("normalized")
    if isinstance(existing, dict) and existing:
        return dict(existing)
    out: Dict[str, Any] = {}
    for key in _NORMALIZED_KEYS:
        if key in row and row[key] is not None:
            out[key] = row[key]
    for key, val in row.items():
        sk = str(key)
        if sk.startswith("__mv_"):
            continue
        if val is not None and sk not in out:
            out[sk] = val
    for key in _NORMALIZED_KEYS:
        if key in payload and payload[key] is not None and key not in out:
            out[key] = payload[key]
    return out


def normalize_splunk_ingest_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    row = _row_from_payload(payload)
    sid = _first_non_empty(payload.get("sid"), payload.get("job_sid"), row.get("sid"))
    search_name = _first_non_empty(
        payload.get("search_name"),
        payload.get("savedsearch_name"),
        row.get("search_name"),
    )
    results: List[Dict[str, Any]] = []
    raw_results = payload.get("results")
    if isinstance(raw_results, list):
        results = [x for x in raw_results if isinstance(x, dict)]
    elif row:
        results = [row]
    return {
        "sid": sid,
        "orig_sid": _first_non_empty(payload.get("orig_sid"), row.get("orig_sid")),
        "search_name": search_name,
        "app": _first_non_empty(payload.get("app")),
        "owner": _first_non_empty(payload.get("owner")),
        "results_link": _first_non_empty(payload.get("results_link")),
        "server_uri": _first_non_empty(payload.get("server_uri")),
        "results": results,
        "normalized": _build_normalized(payload, row),
        "severity_override": _first_non_empty(payload.get("severity_override")),
        "include_raw": _truthy(payload.get("include_raw")),
    }


def to_analysis_route_body(
    handoff: Dict[str, Any],
    *,
    offline: bool,
    row_index: int = 0,
) -> Dict[str, Any]:
    rows = list(handoff.get("results") or [])
    base: Dict[str, Any] = {
        "sid": handoff.get("sid"),
        "search_name": handoff.get("search_name"),
        "row_index": row_index,
    }
    if offline:
        base["normalized"] = handoff.get("normalized") or (rows[0] if rows else {})
        base["splunk_results"] = rows
        return base
    base["normalized"] = handoff.get("normalized") or {}
    base["splunk_results"] = []
    return base


def _apply_route_response(summary: RunSummary, res: Any) -> None:
    if not isinstance(res, dict):
        return
    if res.get("row_index") is not None:
        summary.row_index = int(res["row_index"])
    ra = res.get("raw_alert")
    if isinstance(ra, dict):
        summary.raw_alert = ra
    ai = res.get("analysis_input")
    if isinstance(ai, dict):
        summary.analysis_input = ai
    ao = res.get("analysis_output")
    if isinstance(ao, dict):
        summary.analysis_output = ao
    clf = res.get("classification")
    if isinstance(clf, dict):
        summary.route_track = clf.get("track") or summary.route_track
        summary.route_pipeline = clf.get("recommended_pipeline") or summary.route_pipeline
    sec = res.get("security_result")
    if isinstance(sec, dict):
        judge = sec.get("judge")
        if isinstance(judge, dict) and judge.get("verdict"):
            summary.judge_verdict = str(judge["verdict"])
        if not summary.analysis_output:
            summary.analysis_output = {
                "verdict": judge.get("verdict") if isinstance(judge, dict) else None,
                "priority": judge.get("priority") if isinstance(judge, dict) else None,
                "recommended_next_step": judge.get("recommended_next_step")
                if isinstance(judge, dict)
                else None,
                "summary": sec.get("summary"),
            }


class BackendClient:
    def __init__(self, base_url: str, token: Optional[str], timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer {0}".format(self.token.strip())
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Any]:
        if not path.startswith("/"):
            path = "/" + path
        url = self.base_url + path
        if query:
            url = url + "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
        log.debug("%s %s", method, url)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                status = resp.status
        except urllib.error.HTTPError as e:
            status = e.code
            text = e.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as e:
            raise ScriptError(_explain_exception(e, verbose=False)) from e
        except TimeoutError as e:
            raise ScriptError(
                "Request timed out after {0:.0f}s ({1} {2})".format(
                    self.timeout, method, path
                )
            ) from e
        if not text:
            return status, {}
        try:
            return status, json.loads(text)
        except json.JSONDecodeError:
            return status, text

    def post(self, path: str, body: Dict[str, Any], query: Optional[Dict[str, str]] = None) -> Tuple[int, Any]:
        return self.request("POST", path, body=body, query=query)

    def get(self, path: str, query: Optional[Dict[str, str]] = None) -> Tuple[int, Any]:
        return self.request("GET", path, query=query)


def _print_section(title: str, body: str) -> None:
    print("\n" + "=" * 72, flush=True)
    print(title, flush=True)
    print("=" * 72, flush=True)
    print(body.strip() if body else "(empty)", flush=True)


def _format_value(value: Any, *, indent: int = 0) -> str:
    prefix = "  " * indent
    if isinstance(value, dict):
        lines = []
        for k, v in sorted(value.items(), key=lambda x: str(x[0])):
            if isinstance(v, (dict, list)):
                lines.append("{0}{1}:".format(prefix, k))
                lines.append(_format_value(v, indent=indent + 1))
            else:
                lines.append("{0}{1}: {2}".format(prefix, k, v))
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return prefix + "(none)"
        lines = []
        for i, item in enumerate(value):
            if isinstance(item, (dict, list)):
                lines.append("{0}- [{1}]".format(prefix, i))
                lines.append(_format_value(item, indent=indent + 1))
            else:
                lines.append("{0}- {1}".format(prefix, item))
        return "\n".join(lines)
    return "{0}{1}".format(prefix, value)


def print_investigation_report(route_res: Dict[str, Any]) -> None:
    """Analyst-style narrative from POST /analysis/route (live API response)."""
    print("\n" + "#" * 72, flush=True)
    print("# INVESTIGATION REPORT (API response)", flush=True)
    print("#" * 72, flush=True)

    clf = route_res.get("classification")
    if isinstance(clf, dict):
        _print_section(
            "0) Classification / routing",
            _format_value(
                {
                    "track": clf.get("track"),
                    "recommended_pipeline": clf.get("recommended_pipeline"),
                    "confidence": clf.get("confidence"),
                    "reason": clf.get("reason"),
                    "signals": clf.get("signals"),
                }
            ),
        )

    sec = route_res.get("security_result")
    if not isinstance(sec, dict):
        _print_section("Security pipeline", "(no security_result in response)")
        return

    if sec.get("summary"):
        _print_section("Summary", str(sec.get("summary")))

    _print_section("Defender", str(sec.get("defender") or ""))

    hunter = sec.get("hunter")
    if isinstance(hunter, dict):
        hunt_text = str(hunter.get("narrative") or "")
        sug = hunter.get("splunk_search_suggestions") or []
        if sug:
            hunt_text += "\n\nSplunk search suggestions:\n" + "\n".join("- {0}".format(s) for s in sug)
        _print_section("Hunter", hunt_text)
    else:
        _print_section("Hunter", str(hunter or ""))

    judge = sec.get("judge")
    if isinstance(judge, dict):
        _print_section(
            "Judge",
            _format_value(
                {
                    "verdict": judge.get("verdict"),
                    "priority": judge.get("priority"),
                    "recommended_next_step": judge.get("recommended_next_step"),
                    "confidence": judge.get("confidence"),
                    "rationale": judge.get("rationale"),
                }
            ),
        )

    inv_q = sec.get("investigation_questions") or []
    if inv_q:
        _print_section(
            "Investigation questions",
            "\n".join("{0}. {1}".format(i + 1, q) for i, q in enumerate(inv_q)),
        )

    fw = sec.get("framework_mapping") or []
    if fw:
        _print_section("Framework mapping", _format_value(fw))

    ident = sec.get("identity_resolution")
    if isinstance(ident, dict):
        _print_section("Identity resolution", _format_value(ident))

    if sec.get("risk_context"):
        _print_section("Risk context", str(sec.get("risk_context")))

    rcs = sec.get("root_cause_spl")
    if isinstance(rcs, dict) and rcs.get("spl"):
        _print_section(
            "Root-cause SPL",
            "SPL:\n{0}\n\nExplanation:\n{1}".format(
                rcs.get("spl", ""),
                rcs.get("explanation", ""),
            ),
        )


def _payload_content(payload: Dict[str, Any]) -> Any:
    if "content" in payload:
        return payload["content"]
    if "analysis" in payload:
        return payload["analysis"]
    return payload


def fetch_investigation_from_db(
    client: BackendClient,
    summary: RunSummary,
    *,
    sid: Optional[str],
    row_index: Optional[int] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Load each investigation phase from PostgreSQL via GET /storage/events."""
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    total = 0
    for rec_type in INVESTIGATION_DB_TYPES:
        query: Dict[str, str] = {"record_type": rec_type, "limit": "10"}
        if sid:
            query["sid"] = sid
        if row_index is not None:
            query["row_index"] = str(row_index)
        st, body = client.get("/api/v1/storage/events", query=query)
        if st >= 400:
            log.warning("storage/events %s → HTTP %d", rec_type, st)
            continue
        if not isinstance(body, dict):
            continue
        rows = body.get("results") or []
        if not rows:
            continue
        by_type[rec_type] = [r for r in rows if isinstance(r, dict)]
        total += len(by_type[rec_type])
        log.info("DB: loaded %d row(s) type=%s", len(by_type[rec_type]), rec_type)
    summary.db_phase_records = total
    summary.stored_events = total
    return by_type


def print_investigation_from_db(by_type: Dict[str, List[Dict[str, Any]]]) -> None:
    """Print analyst narrative from records returned by the storage API."""
    print("\n" + "#" * 72, flush=True)
    print("# INVESTIGATION REPORT (from PostgreSQL via /storage/events)", flush=True)
    print("#" * 72, flush=True)

    if not by_type:
        _print_section(
            "Database",
            "No investigation rows found. Restart backend after the JSONB fix, then re-run this script.",
        )
        return

    for rec_type in INVESTIGATION_DB_TYPES:
        rows = by_type.get(rec_type) or []
        if not rows:
            continue
        row = rows[0]
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else row
        if not isinstance(payload, dict):
            continue

        if rec_type == "soc_analysis_audit":
            _print_section(
                "Analysis audit (soc_analysis_audit)",
                _format_value(
                    {
                        "sid": payload.get("sid"),
                        "search_name": payload.get("search_name"),
                        "row_index": payload.get("row_index"),
                        "raw_alert": payload.get("raw_alert"),
                        "analysis_input": payload.get("analysis_input"),
                        "analysis_output": payload.get("analysis_output"),
                    }
                ),
            )
            continue

        if rec_type == "agentic_ops_analysis":
            _print_section(
                "Routed analysis (agentic_ops_analysis)",
                _format_value(
                    {
                        "row_index": payload.get("row_index"),
                        "raw_alert": payload.get("raw_alert"),
                        "analysis_input": payload.get("analysis_input"),
                        "analysis_output": payload.get("analysis_output"),
                        "classification": payload.get("classification"),
                        "security_result": "(see phase rows below)",
                    }
                ),
            )
            continue

        if rec_type == "soc_analysis":
            analysis = payload.get("analysis")
            if isinstance(analysis, dict):
                print_investigation_report({"classification": {}, "security_result": analysis})
            continue

        phase = str(payload.get("phase") or rec_type.replace("soc_investigation_", ""))
        title = _PHASE_LABELS.get(phase, phase)
        content = _payload_content(payload)
        if phase in ("raw_alert", "alert_fields") and isinstance(content, dict):
            body = _format_value(content)
        elif phase == "investigation_questions" and isinstance(content, list):
            body = "\n".join("{0}. {1}".format(i + 1, q) for i, q in enumerate(content))
        elif phase == "hunter" and isinstance(content, dict):
            body = str(content.get("narrative") or "")
            sug = content.get("splunk_search_suggestions") or []
            if sug:
                body += "\n\nSplunk search suggestions:\n" + "\n".join("- {0}".format(s) for s in sug)
        elif phase == "root_cause_spl" and isinstance(content, dict):
            body = "SPL:\n{0}\n\nExplanation:\n{1}".format(
                content.get("spl", ""),
                content.get("explanation", ""),
            )
        elif isinstance(content, (dict, list)):
            body = _format_value(content)
        else:
            body = str(content)
        _print_section("{0} [{1}]".format(title, rec_type), body)


def poll_storage_events(
    client: BackendClient,
    summary: RunSummary,
    *,
    sid: Optional[str],
    record_type: str,
    limit: int,
    timeout_sec: float,
    interval_sec: float,
    verbose: bool,
) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout_sec
    last: Dict[str, Any] = {"count": 0, "results": [], "postgres_configured": False}
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        query: Dict[str, str] = {"record_type": record_type, "limit": str(limit)}
        if sid:
            query["sid"] = sid
        status, body = client.get("/api/v1/storage/events", query=query)
        summary.http["GET /storage/events"] = status
        if status >= 400:
            summary.fail("storage/events returned HTTP {0}".format(status))
            _log_json("storage/events error body", body, verbose=verbose)
            return last
        if isinstance(body, dict):
            last = body
            count = int(body.get("count") or 0)
            log.info("Poll attempt %d: %d event(s) for record_type=%s", attempt, count, record_type)
            if count > 0:
                summary.stored_events = count
                return body
        time.sleep(interval_sec)
    summary.stored_events = int(last.get("count") or 0)
    log.warning("Poll finished with no new events (timeout %.0fs)", timeout_sec)
    return last


def run_console(
    client: BackendClient,
    handoff: Dict[str, Any],
    summary: RunSummary,
    *,
    offline: bool,
    row_index: int,
    verbose: bool,
) -> int:
    body = to_analysis_route_body(handoff, offline=offline, row_index=row_index)
    summary.step("POST /api/v1/analysis/route")
    _log_json("Route request body", body, verbose=verbose)
    status, res = client.post("/api/v1/analysis/route", body)
    summary.http["POST /analysis/route"] = status
    log.info("analysis/route → HTTP %d", status)
    if status >= 400:
        hint = ""
        if status == 502:
            hint = " (Splunk REST down? use auto --offline or start Splunk on :8089)"
        summary.fail("analysis/route failed (HTTP {0}){1}".format(status, hint))
        _log_json("Error response", res, verbose=True)
        return 1
    _apply_route_response(summary, res)
    if isinstance(res, dict):
        print_investigation_report(res)

    summary.step("Load investigation phases from PostgreSQL")
    by_type = fetch_investigation_from_db(
        client,
        summary,
        sid=str(handoff["sid"]) if handoff.get("sid") else None,
        row_index=summary.row_index,
    )
    print_investigation_from_db(by_type)
    audit = extract_audit_from_db(by_type)
    if audit:
        if isinstance(audit.get("raw_alert"), dict):
            summary.raw_alert = audit["raw_alert"]
        if isinstance(audit.get("analysis_input"), dict):
            summary.analysis_input = audit["analysis_input"]
        if isinstance(audit.get("analysis_output"), dict):
            summary.analysis_output = audit["analysis_output"]
        if audit.get("row_index") is not None:
            summary.row_index = int(audit["row_index"])
    fields, src = resolve_analysis_fields(handoff, by_type, row_index=summary.row_index)
    summary.analysis_fields = fields
    summary.analysis_fields_source = src
    if summary.db_phase_records == 0:
        log.warning(
            "No rows in DB yet — restart backend (JSONB fix) and re-run; "
            "phases are stored as soc_investigation_* + soc_analysis"
        )
    return 0


def run_webhook(
    client: BackendClient,
    payload: Dict[str, Any],
    handoff: Dict[str, Any],
    summary: RunSummary,
    *,
    poll: bool,
    poll_timeout: float,
    verbose: bool,
) -> int:
    summary.step("POST /api/v1/alerts/splunk-ingest")
    _log_json("Webhook payload", payload, verbose=verbose)
    status, res = client.post("/api/v1/alerts/splunk-ingest", payload)
    summary.http["POST /splunk-ingest"] = status
    log.info("splunk-ingest → HTTP %d", status)
    _log_json("Ingest response", res, verbose=verbose)
    if status >= 400:
        summary.fail("splunk-ingest failed (HTTP {0})".format(status))
        return 1
    if isinstance(res, dict):
        summary.ingest_status = res.get("status") or ("ok" if res.get("ok") else None)
        if res.get("job_id"):
            log.info("Background job_id: %s", res.get("job_id"))

    if poll and handoff.get("sid"):
        summary.step("Poll /storage/events until soc_analysis appears")
        poll_storage_events(
            client,
            summary,
            sid=str(handoff["sid"]),
            record_type="soc_analysis",
            limit=50,
            timeout_sec=poll_timeout,
            interval_sec=2.0,
            verbose=verbose,
        )
    return 0


def parse_args() -> argparse.Namespace:
    base, token = _resolve_config()
    p = argparse.ArgumentParser(
        description="Test Splunk webhook JSON (log output + result summary)",
    )
    p.add_argument("json_file", type=Path, help="Splunk webhook / alert JSON file")
    p.add_argument(
        "--mode",
        choices=("console", "webhook", "full"),
        default="console",
        help="console=analysis/route; webhook=splunk-ingest; full=webhook+poll",
    )
    p.add_argument("--dry-run", action="store_true", help="Only parse JSON; no HTTP")
    p.add_argument(
        "--offline",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="console: send result rows from JSON (default: auto when JSON has result/results)",
    )
    p.add_argument(
        "--live-splunk",
        action="store_true",
        help="console: always call Splunk REST for job rows (needs Splunk on SPLUNK_MGMT_URL)",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Log full JSON bodies (DEBUG)")
    p.add_argument("--base-url", default=base, help="Backend base URL")
    p.add_argument("--token", default=token, help="TSOC_INGEST_TOKEN")
    p.add_argument("--no-poll", action="store_true")
    p.add_argument("--poll-timeout", type=float, default=120.0)
    p.add_argument("--timeout", type=float, default=300.0)
    p.add_argument(
        "--row-index",
        type=int,
        default=0,
        help="Splunk result row to analyze (default 0). Stored in PostgreSQL as row_index.",
    )
    return p.parse_args()


def _resolve_offline(args: argparse.Namespace, handoff: Dict[str, Any], mode: str) -> bool:
    """Use JSON rows by default so captured webhook files work without a live Splunk."""
    if args.live_splunk:
        return False
    if args.offline is not None:
        return bool(args.offline)
    if mode == "console" and handoff.get("results"):
        return True
    return False


def _resolve_json_path(arg: Path) -> Path:
    """Resolve JSON path: repo root, script dir (scripts/), then cwd."""
    if arg.is_absolute():
        return arg
    for base in (REPO_ROOT, SCRIPT_DIR, Path.cwd()):
        candidate = (base / arg).resolve()
        if candidate.is_file():
            return candidate
    return (REPO_ROOT / arg).resolve()


def main() -> int:
    args = parse_args()
    setup_logging(verbose=args.verbose)

    path = _resolve_json_path(args.json_file)
    summary = RunSummary(
        mode=args.mode,
        json_file=str(path),
        dry_run=args.dry_run,
        offline=bool(args.offline) if args.offline is not None else False,
        base_url=args.base_url,
    )

    exit_code = 0
    try:
        if not path.is_file():
            raise ScriptError("File not found: {0}".format(path))

        summary.step("Load JSON: {0}".format(path.name))
        payload = _load_json(path)
        handoff = normalize_splunk_ingest_payload(payload)
        summary.sid = handoff.get("sid")
        summary.search_name = handoff.get("search_name")
        summary.row_index = max(0, int(args.row_index))
        summary.splunk_results_row_count = len(handoff.get("results") or [])
        rows = list(handoff.get("results") or [])
        if rows and summary.row_index >= len(rows):
            summary.row_index = len(rows) - 1
        log.info(
            "Parsed handoff: sid=%s search_name=%s row_index=%d result_rows=%d",
            summary.sid or "(none)",
            summary.search_name or "(none)",
            summary.row_index,
            summary.splunk_results_row_count,
        )
        _log_json("Normalized handoff", handoff, verbose=args.verbose)

        offline = _resolve_offline(args, handoff, args.mode)
        summary.offline = offline
        summary.raw_alert = {
            "sid": summary.sid,
            "search_name": summary.search_name,
            "row_index": summary.row_index,
            "splunk_results_row_count": summary.splunk_results_row_count,
            "normalized": handoff.get("normalized") or {},
            "result_row": rows[summary.row_index] if rows else None,
        }
        preview_fields = build_alert_fields_for_summary(
            search_name=handoff.get("search_name"),
            normalized=handoff.get("normalized") or {},
            splunk_results=rows,
            row_index=summary.row_index,
        )
        summary.analysis_fields = preview_fields
        summary.analysis_fields_source = "webhook JSON (preview)"
        summary.analysis_input = {
            "row_index": summary.row_index,
            "alert_fields": preview_fields,
        }
        if offline and args.offline is None and not args.live_splunk and handoff.get("results"):
            log.info(
                "Auto offline mode: using %d row(s) from JSON (no Splunk REST on :8089)",
                len(handoff.get("results") or []),
            )
        elif args.live_splunk:
            log.info("Live Splunk mode: backend will enrich via Splunk REST (requires Splunk running)")

        if args.dry_run:
            summary.step("Dry run — skipped HTTP")
            if summary.analysis_fields:
                log.info(
                    "Fields that would be sent to analysis (%d): %s",
                    len(summary.analysis_fields),
                    ", ".join(sorted(summary.analysis_fields.keys())),
                )
            if not summary.sid:
                log.warning("sid missing — live ingest/route will need a valid Splunk sid")
            return 0

        if not handoff.get("sid") and args.mode != "console":
            log.warning("sid missing — splunk-ingest needs sid for Splunk REST enrich")

        client = BackendClient(args.base_url, args.token, args.timeout)
        log.info("Backend %s | Bearer %s", args.base_url, "set" if args.token else "none")

        if args.mode == "console":
            exit_code = run_console(
                client,
                handoff,
                summary,
                offline=offline,
                row_index=summary.row_index,
                verbose=args.verbose,
            )
        elif args.mode == "webhook":
            exit_code = run_webhook(
                client,
                payload,
                handoff,
                summary,
                poll=not args.no_poll,
                poll_timeout=args.poll_timeout,
                verbose=args.verbose,
            )
        else:
            exit_code = run_webhook(
                client,
                payload,
                handoff,
                summary,
                poll=False,
                poll_timeout=args.poll_timeout,
                verbose=args.verbose,
            )
            if exit_code == 0 and not args.no_poll and handoff.get("sid"):
                summary.step("Poll /storage/events (full mode)")
                poll_storage_events(
                    client,
                    summary,
                    sid=str(handoff["sid"]),
                    record_type="soc_analysis",
                    limit=50,
                    timeout_sec=args.poll_timeout,
                    interval_sec=2.0,
                    verbose=args.verbose,
                )
    except ScriptError as e:
        summary.fail(str(e))
        exit_code = 1
    except KeyboardInterrupt:
        summary.fail("Stopped by user (Ctrl+C)")
        log.warning("Interrupted")
        exit_code = 130
    except Exception as e:
        summary.fail(_explain_exception(e, verbose=args.verbose))
        if args.verbose:
            log.error("Traceback:\n%s", traceback.format_exc())
        else:
            log.error(
                "Unexpected error (%s). Re-run with -v for full traceback.",
                type(e).__name__,
            )
        exit_code = 1
    finally:
        print_result_summary(summary)

    return exit_code


def cli() -> int:
    """Entry point: never crash without a summary message."""
    try:
        return main()
    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C).", file=sys.stderr)
        return 130
    except Exception as e:
        print("\nFatal error: {0}".format(_explain_exception(e, verbose=False)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
