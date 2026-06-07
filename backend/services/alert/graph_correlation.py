"""Derive Neo4j correlation fields from Splunk webhook rows (no campaign hardcoding)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from config import Settings
from models.enrichment import EnrichmentResult
from models.handoff import SplunkAlertIngest, normalize_splunk_ingest_payload
from services.alert.enrichment_resolver import enrich_from_inventory
from services.inventory.assets import list_assets
from services.inventory.converters import asset_record_to_dict, user_record_to_dict
from services.inventory.relationships import list_relationships
from services.inventory.users import list_users

_HOST_KEYS = ("host", "hostname", "Computer", "dest_host", "dest")
_USER_KEYS = ("user", "User", "src_user", "dest_user", "account")
_IP_KEYS = (
    "src_ip",
    "dest_ip",
    "ip",
    "src",
    "dest",
    "related_src_ip",
    "related_dest_ip",
    "ioc_ip",
    "threat_ip",
    "external_ip",
)
_SEVERITY_RISK = {"low": 40, "medium": 55, "high": 70, "critical": 85}


def _first(row: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        val = row.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def _is_private_ip(ip: str) -> bool:
    if ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("127."):
        return True
    if ip.startswith("172."):
        parts = ip.split(".")
        if len(parts) >= 2:
            try:
                second = int(parts[1])
                return 16 <= second <= 31
            except ValueError:
                pass
    return False


def derive_alert_row_id(*, sid: str, search_name: str = "") -> str:
    """Stable alert id from Splunk job id (same sid → same graph node)."""
    raw = f"{sid.strip()}|{search_name.strip()}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:12].upper()
    return f"ALERT-{digest}"


def normalize_row_data(row: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in row.items() if not str(k).startswith("__mv_")}
    host = _first(row, _HOST_KEYS)
    user = _first(row, _USER_KEYS)
    if host:
        out["host"] = host
    if user:
        out["user"] = user
    if row.get("src_ip") and "src" not in out:
        out["src"] = row["src_ip"]
    if row.get("dest_ip") and "dest" not in out:
        out["dest"] = row["dest_ip"]
    return out


def build_entity_identifiers(
    normalized: dict[str, Any],
    enrichment: EnrichmentResult | None = None,
) -> list[str]:
    ids: list[str] = []
    host = _first(normalized, _HOST_KEYS)
    if host:
        ids.append(f"hostname:{host}")
    user = _first(normalized, _USER_KEYS)
    if user:
        ids.append(f"username:{user}")
    elif enrichment and enrichment.resolved_user_id:
        ids.append(f"username:{enrichment.resolved_user_id}")
    for key in _IP_KEYS:
        val = normalized.get(key)
        if not val:
            continue
        ip = str(val).strip()
        if not ip or _is_private_ip(ip):
            continue
        tag = f"ipv4:{ip}"
        if tag not in ids:
            ids.append(tag)
    return ids


def _severity_risk(row: dict[str, Any], payload: dict[str, Any]) -> int:
    for source in (row, payload):
        val = source.get("severity")
        if val is not None and str(val).strip():
            return _SEVERITY_RISK.get(str(val).strip().lower(), 55)
    return 55


def _time_to_iso(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if text.endswith("Z") or "T" in text:
        return text
    try:
        ts = int(text)
    except (TypeError, ValueError):
        return text
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_correlation_block(
    *,
    handoff: SplunkAlertIngest,
    enrichment: EnrichmentResult | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    row = dict(handoff.results[0]) if handoff.results else dict(handoff.normalized or {})
    normalized = normalize_row_data(row)
    entities = build_entity_identifiers(normalized, enrichment)
    sid = str(handoff.sid or "").strip()
    search_name = str(handoff.search_name or "").strip()
    alert_row_id = derive_alert_row_id(sid=sid, search_name=search_name)
    existing = payload.get("correlation")
    if isinstance(existing, dict) and existing.get("alert_row_id"):
        alert_row_id = str(existing["alert_row_id"])

    return {
        "alert_row_id": alert_row_id,
        "entity_identifiers": entities,
        "risk_score": _severity_risk(row, payload),
        "timestamp": _time_to_iso(normalized.get("_time") or row.get("_time")),
        "status": "open",
    }


async def _load_inventory(settings: Settings) -> tuple[list[dict], list[dict], list[dict]]:
    users = [user_record_to_dict(u) for u in await list_users(settings)]
    assets = [asset_record_to_dict(a) for a in await list_assets(settings)]
    rels = [
        {
            "relationship_id": r.relationship_id,
            "user_id": r.user_id,
            "asset_id": r.asset_id,
            "description": r.description,
        }
        for r in await list_relationships(settings)
    ]
    return users, assets, rels


async def ensure_graph_correlation_on_payload(
    payload: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    """Attach or refresh correlation block from alert fields + inventory (no manifest)."""
    corr = payload.get("correlation")
    if isinstance(corr, dict) and corr.get("alert_row_id") and corr.get("entity_identifiers"):
        return payload

    handoff = normalize_splunk_ingest_payload(payload)
    enrichment: EnrichmentResult | None = None
    pre = payload.get("enrichment")
    if isinstance(pre, dict) and pre.get("resolved_asset_id") is not None:
        try:
            enrichment = EnrichmentResult.model_validate(pre)
        except Exception:
            enrichment = None
    if enrichment is None and settings.tsoc_postgres_dsn:
        row = dict(handoff.results[0]) if handoff.results else dict(handoff.normalized or {})
        normalized = normalize_row_data(row)
        users, assets, rels = await _load_inventory(settings)
        enrichment = enrich_from_inventory(normalized, users, assets, rels)

    out = dict(payload)
    out["correlation"] = build_correlation_block(
        handoff=handoff,
        enrichment=enrichment,
        payload=payload,
    )
    return out
