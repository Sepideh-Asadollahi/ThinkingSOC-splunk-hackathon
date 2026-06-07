"""Build compact RAG documents from Splunk alerts (essential fields only)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

from services.alert.alert_fields import _merge_result_row

from .models import RagAlertDocument

RAG_ESSENTIAL_KEYS: tuple[str, ...] = (
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

_DENY_EXACT = frozenset(
    {
        "_raw",
        "password",
        "passwd",
        "token",
        "api_key",
        "authorization",
        "cookie",
    }
)
_DENY_PREFIX = ("__mv_",)
_MAX_FIELD_LEN = 2048
_MAX_EXTRA_KEYS = 5


def _is_denied_key(key: str) -> bool:
    lk = key.lower()
    if lk in _DENY_EXACT:
        return True
    for p in _DENY_PREFIX:
        if lk.startswith(p):
            return True
    if lk.endswith("_link") or lk.endswith("_uri"):
        return True
    return False


def _coerce_essential_value(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, (list, dict)):
        return None
    s = str(val).strip()
    if not s or len(s) > _MAX_FIELD_LEN:
        return None
    return s


def extract_essential_fields(
    merged: Dict[str, Any],
    *,
    extra_keys: Optional[Sequence[str]] = None,
) -> Dict[str, str]:
    out: Dict[str, str] = {}
    keys = list(RAG_ESSENTIAL_KEYS)
    if extra_keys:
        for k in extra_keys[:_MAX_EXTRA_KEYS]:
            sk = str(k).strip()
            if sk and sk not in keys:
                keys.append(sk)
    for key in keys:
        if _is_denied_key(key):
            continue
        v = _coerce_essential_value(merged.get(key))
        if v is not None:
            out[key] = v
    return out


def _build_summary_line(
    search_name: Optional[str],
    essential: Dict[str, str],
) -> str:
    parts: List[str] = []
    t = essential.get("_time")
    if t:
        parts.append(t[:19] if len(t) > 19 else t)
    sn = (search_name or "").strip()
    if sn:
        parts.append(sn)
    ent_bits: List[str] = []
    for k in ("user", "src", "dest", "host"):
        if essential.get(k):
            ent_bits.append("{0}={1}".format(k, essential[k]))
    if ent_bits:
        parts.append(" ".join(ent_bits))
    sig = essential.get("signature") or essential.get("signature_id")
    if sig:
        parts.append(sig)
    sev = essential.get("severity")
    if sev:
        parts.append("severity={0}".format(sev))
    return " | ".join(parts) if parts else sn or "alert"


def _build_chunk_text(
    *,
    doc_type: str,
    sid: Optional[str],
    search_name: Optional[str],
    essential: Dict[str, str],
    extra_lines: Optional[List[str]] = None,
) -> str:
    lines: List[str] = []
    sn = (search_name or "").strip() or "alert"
    if doc_type == "soc_analysis":
        lines.append("SOC analysis: {0}".format(sn))
    elif doc_type == "observability_analysis":
        lines.append("Observability analysis: {0}".format(sn))
    elif doc_type == "inventory_user":
        lines.append("Inventory user: {0}".format(essential.get("user_id") or sn))
    elif doc_type == "inventory_asset":
        lines.append("Inventory asset: {0}".format(essential.get("asset_id") or sn))
    elif doc_type == "inventory_relationship":
        lines.append(
            "Inventory relationship: user={0} asset={1}".format(
                essential.get("user_id") or "-",
                essential.get("asset_id") or "-",
            )
        )
    elif doc_type.startswith("inventory_"):
        lines.append("Inventory: {0}".format(sn))
    else:
        lines.append("Alert: {0}".format(sn))
    if sid:
        lines.append("sid: {0}".format(sid))
    if essential.get("_time"):
        lines.append("Time: {0}".format(essential["_time"]))
    ent = []
    for k in ("user", "src", "dest", "host"):
        if essential.get(k):
            ent.append("{0}={1}".format(k, essential[k]))
    if ent:
        lines.append("Entities: " + " ".join(ent))
    sig = essential.get("signature") or essential.get("signature_id")
    if sig:
        lines.append("Signal: {0}".format(sig))
    if essential.get("severity"):
        lines.append("Severity: {0}".format(essential["severity"]))
    if doc_type.startswith("inventory_"):
        field_bits = [
            "{0}={1}".format(k, v)
            for k, v in essential.items()
            if v and k not in ("_time",)
        ]
        if field_bits:
            lines.append("Fields: " + " ".join(field_bits))
    if extra_lines:
        for ln in extra_lines:
            if ln and ln.strip():
                lines.append(ln.strip())
    return "\n".join(lines)


def make_doc_id(sid: Optional[str], row_index: int, doc_type: str = "splunk_alert") -> str:
    base = (sid or "unknown").strip() or "unknown"
    safe = re.sub(r"[^a-zA-Z0-9_.\-:]+", "_", base)[:200]
    return "{0}::{1}::{2}".format(doc_type, safe, int(row_index))


def compact_alert_document(
    *,
    sid: Optional[str],
    search_name: Optional[str],
    normalized: Dict[str, Any],
    splunk_results: Optional[List[Dict[str, Any]]] = None,
    row_index: int = 0,
    track: Optional[str] = None,
    verdict: Optional[str] = None,
    extra_keys: Optional[Sequence[str]] = None,
) -> RagAlertDocument:
    merged = _merge_result_row(normalized or {}, splunk_results or [], row_index=row_index)
    essential = extract_essential_fields(merged, extra_keys=extra_keys)
    summary_line = _build_summary_line(search_name, essential)
    chunk_text = _build_chunk_text(
        doc_type="splunk_alert",
        sid=sid,
        search_name=search_name,
        essential=essential,
    )
    meta: Dict[str, Any] = {
        "sid": sid,
        "search_name": search_name,
        "row_index": row_index,
        "doc_type": "splunk_alert",
    }
    for k, v in essential.items():
        meta[k] = v
    if track:
        meta["track"] = track
    if verdict:
        meta["verdict"] = verdict
    doc_id = make_doc_id(sid, row_index, "splunk_alert")
    return RagAlertDocument(
        doc_type="splunk_alert",
        doc_id=doc_id,
        sid=sid,
        search_name=search_name,
        row_index=row_index,
        essential=essential,
        summary_line=summary_line,
        chunk_text=chunk_text,
        metadata=meta,
    )
