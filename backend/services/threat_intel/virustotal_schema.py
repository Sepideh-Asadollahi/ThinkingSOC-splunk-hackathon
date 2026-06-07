"""
VirusTotal API v3 response shapes (official docs).

References:
- https://docs.virustotal.com/reference/api-responses
- https://docs.virustotal.com/reference/ip-object
- https://docs.virustotal.com/reference/domains-object
- https://docs.virustotal.com/reference/url-object
- https://docs.virustotal.com/reference/files
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Optional, Tuple

# Top-level envelope: {"data": { "id", "type", "links", "attributes" }}
VT_ENVELOPE_DATA_KEY = "data"

# `data.type` values returned by VT (object discriminator)
VT_TYPE_FILE = "file"
VT_TYPE_IP = "ip_address"
VT_TYPE_DOMAIN = "domain"
VT_TYPE_URL = "url"

# REST paths (API v3)
VT_PATH_FILES = "/files/{id}"
VT_PATH_IP = "/ip_addresses/{id}"
VT_PATH_DOMAIN = "/domains/{id}"
VT_PATH_URL = "/urls/{id}"

# `attributes.last_analysis_stats` — IP / domain / URL (docs.virustotal.com)
VT_STATS_NETWORK_KEYS: FrozenSet[str] = frozenset(
    {"harmless", "malicious", "suspicious", "timeout", "undetected"}
)

# `attributes.last_analysis_stats` — file object adds these keys (docs.virustotal.com)
VT_STATS_FILE_EXTRA_KEYS: FrozenSet[str] = frozenset(
    {"confirmed-timeout", "failure", "type-unsupported"}
)

VT_STATS_ALL_KNOWN_KEYS: FrozenSet[str] = VT_STATS_NETWORK_KEYS | VT_STATS_FILE_EXTRA_KEYS

# `attributes.total_votes` — all object types
VT_TOTAL_VOTES_KEYS: FrozenSet[str] = frozenset({"harmless", "malicious"})


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def normalize_last_analysis_stats(raw: Any, *, vt_type: str) -> Dict[str, int]:
    """
    Keep only documented stat keys; coerce to int.
    Unknown keys from VT are preserved (forward-compatible).
    """
    if not isinstance(raw, dict):
        return {}
    allowed = VT_STATS_ALL_KNOWN_KEYS if vt_type == VT_TYPE_FILE else VT_STATS_NETWORK_KEYS
    out: Dict[str, int] = {}
    for key, val in raw.items():
        if key in allowed:
            out[key] = _as_int(val)
    return out


def normalize_total_votes(raw: Any) -> Dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    return {k: _as_int(raw.get(k)) for k in VT_TOTAL_VOTES_KEYS if raw.get(k) is not None}


def extract_vt_object(api_json: Optional[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Parse standard VT v3 envelope. Returns (object_dict, error).
    object_dict keys: id, type, link, attributes (raw attributes only).
    """
    if not api_json or not isinstance(api_json, dict):
        return None, "empty_response"
    data = api_json.get(VT_ENVELOPE_DATA_KEY)
    if not isinstance(data, dict):
        return None, "missing_data"
    attrs = data.get("attributes")
    if not isinstance(attrs, dict):
        return None, "missing_attributes"
    links = data.get("links") if isinstance(data.get("links"), dict) else {}
    return (
        {
            "id": data.get("id"),
            "type": data.get("type"),
            "link": links.get("self"),
            "attributes": attrs,
        },
        None,
    )


def build_vt_summary(api_json: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    High-signal subset of a VT object using **official attribute names** only.

    Shape is stable for SOC prompts; nested objects match VT field names.
    """
    obj, err = extract_vt_object(api_json)
    if err or not obj:
        return None

    vt_type = str(obj.get("type") or "")
    attrs = obj["attributes"]

    summary: Dict[str, Any] = {
        "id": obj.get("id"),
        "type": vt_type,
        "link": obj.get("link"),
        "last_analysis_date": attrs.get("last_analysis_date"),
        "last_analysis_stats": normalize_last_analysis_stats(
            attrs.get("last_analysis_stats"), vt_type=vt_type
        ),
        "reputation": attrs.get("reputation"),
        "total_votes": normalize_total_votes(attrs.get("total_votes")),
        "tags": attrs.get("tags") if isinstance(attrs.get("tags"), list) else [],
    }

    # `categories` exists on domain + URL objects (partner categorization dict)
    if vt_type in (VT_TYPE_DOMAIN, VT_TYPE_URL) and isinstance(attrs.get("categories"), dict):
        summary["categories"] = attrs["categories"]

    # File-specific identifiers (official file attributes)
    if vt_type == VT_TYPE_FILE:
        for key in ("md5", "sha1", "sha256", "meaningful_name", "type_description"):
            if attrs.get(key) is not None:
                summary[key] = attrs.get(key)

    return summary


def stats_imply_malicious(stats: Dict[str, int]) -> bool:
    return stats.get("malicious", 0) > 0


def stats_imply_suspicious(stats: Dict[str, int]) -> bool:
    return stats.get("suspicious", 0) > 0 and stats.get("malicious", 0) == 0
