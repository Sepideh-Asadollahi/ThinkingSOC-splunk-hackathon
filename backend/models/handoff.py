from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SplunkAlertIngest(BaseModel):
    """Payload posted by the Splunk modular alert action (see LLD section 4)."""

    sid: Optional[str] = None
    orig_sid: Optional[str] = None
    search_name: Optional[str] = None
    app: Optional[str] = None
    owner: Optional[str] = None
    results_link: Optional[str] = None
    server_uri: Optional[str] = None
    results: List[Dict[str, Any]] = Field(default_factory=list)
    normalized: Dict[str, Any] = Field(default_factory=dict)
    # LLD §4.3 — optional operator params from Alert Action UI
    severity_override: Optional[str] = None
    include_raw: bool = False


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
    # Include every other Splunk result field (e.g. count, custom extractions).
    for key, val in row.items():
        sk = str(key)
        if sk.startswith("__mv_"):
            continue
        if val is not None and sk not in out:
            out[sk] = val
    # Some webhook integrations can send row fields at top-level.
    for key in _NORMALIZED_KEYS:
        if key in payload and payload[key] is not None and key not in out:
            out[key] = payload[key]
    return out


def normalize_splunk_ingest_payload(payload: Dict[str, Any]) -> SplunkAlertIngest:
    """
    Normalize both custom-action payload and built-in Splunk webhook payload.

    Splunk webhook payload typically contains:
    - sid
    - search_name
    - result (first result row)
    """
    row = _row_from_payload(payload)
    sid = _first_non_empty(payload.get("sid"), payload.get("job_sid"), row.get("sid"))
    search_name = _first_non_empty(payload.get("search_name"), payload.get("savedsearch_name"), row.get("search_name"))

    results: List[Dict[str, Any]] = []
    raw_results = payload.get("results")
    if isinstance(raw_results, list):
        results = [x for x in raw_results if isinstance(x, dict)]
    elif row:
        results = [row]

    return SplunkAlertIngest(
        sid=sid,
        orig_sid=_first_non_empty(payload.get("orig_sid"), row.get("orig_sid")),
        search_name=search_name,
        app=_first_non_empty(payload.get("app")),
        owner=_first_non_empty(payload.get("owner")),
        results_link=_first_non_empty(payload.get("results_link")),
        server_uri=_first_non_empty(payload.get("server_uri")),
        results=results,
        normalized=_build_normalized(payload, row),
        severity_override=_first_non_empty(payload.get("severity_override")),
        include_raw=_truthy(payload.get("include_raw")),
    )
