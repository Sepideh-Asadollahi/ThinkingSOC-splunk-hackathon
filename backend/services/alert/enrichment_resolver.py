"""Enrich alerts from inventory rows and user–asset relationships."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from models.enrichment import EnrichmentResult

_CRIT_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}

# Built-in alert field → inventory column mappings (replaces configurable identity rules).
_ASSET_ALERT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("host", "hostname"),
    ("hostname", "hostname"),
    ("dest", "hostname"),
    ("dest_host", "hostname"),
    ("src", "ip"),
    ("src_ip", "ip"),
    ("dest_ip", "ip"),
    ("ip", "ip"),
)
_USER_ALERT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("user", "user_id"),
    ("username", "user_id"),
    ("src_user", "user_id"),
    ("dest_user", "user_id"),
    ("account", "user_id"),
    ("user", "email"),
    ("username", "email"),
)


def _norm_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _rows_matching_exact(
    rows: List[Dict[str, Any]],
    field: str,
    needle: str,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        key = field
        if key not in row:
            lower_map = {k.lower(): k for k in row.keys()}
            if field.lower() in lower_map:
                key = lower_map[field.lower()]
        raw = row.get(key)
        if raw is None:
            continue
        if _norm_str(raw) == needle:
            out.append(row)
    return out


def _pick_asset_row(candidates: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], str]:
    if len(candidates) == 1:
        return candidates[0], "high"
    best = candidates[0]
    best_rank = _CRIT_RANK.get(_norm_str(best.get("criticality")).lower(), 0)
    for row in candidates[1:]:
        r = _CRIT_RANK.get(_norm_str(row.get("criticality")).lower(), 0)
        if r > best_rank:
            best = row
            best_rank = r
    return best, "medium"


def _pick_user_row(candidates: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], str]:
    if len(candidates) == 1:
        return candidates[0], "high"
    return candidates[0], "medium"


def _match_assets(normalized: Dict[str, Any], assets: List[Dict[str, Any]]) -> Tuple[Optional[str], str, List[str]]:
    notes: List[str] = []
    lowest = "high"
    for alert_field, inv_field in _ASSET_ALERT_FIELDS:
        needle = _norm_str(normalized.get(alert_field))
        if not needle:
            continue
        candidates = _rows_matching_exact(assets, inv_field, needle)
        if not candidates:
            continue
        row, conf = _pick_asset_row(candidates)
        aid = _norm_str(row.get("asset_id"))
        if aid:
            notes.append("Matched asset via alert.{0} → {1}".format(alert_field, inv_field))
            if conf == "medium" and lowest == "high":
                lowest = "medium"
            return aid, conf, notes
    return None, "low", notes


def _match_users(normalized: Dict[str, Any], users: List[Dict[str, Any]]) -> Tuple[Optional[str], str, List[str]]:
    notes: List[str] = []
    lowest = "high"
    seen_fields: set[str] = set()
    for alert_field, inv_field in _USER_ALERT_FIELDS:
        key = (alert_field, inv_field)
        if key in seen_fields:
            continue
        seen_fields.add(key)
        needle = _norm_str(normalized.get(alert_field))
        if not needle:
            continue
        candidates = _rows_matching_exact(users, inv_field, needle)
        if not candidates:
            continue
        row, conf = _pick_user_row(candidates)
        uid = _norm_str(row.get("user_id"))
        if uid:
            notes.append("Matched user via alert.{0} → {1}".format(alert_field, inv_field))
            if conf == "medium" and lowest == "high":
                lowest = "medium"
            return uid, conf, notes
    return None, "low", notes


def _asset_criticality_rank(asset_id: str, assets: List[Dict[str, Any]]) -> int:
    for row in assets:
        if _norm_str(row.get("asset_id")) == asset_id:
            return _CRIT_RANK.get(_norm_str(row.get("criticality")).lower(), 0)
    return 0


def _user_risk_rank(user_id: str, users: List[Dict[str, Any]]) -> int:
    for row in users:
        if _norm_str(row.get("user_id")) == user_id:
            try:
                return int(row.get("risk_score") or 0)
            except (TypeError, ValueError):
                return 0
    return 0


def _pick_relationship_for_user(
    user_id: str,
    relationships: List[Dict[str, Any]],
    assets: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    candidates = [r for r in relationships if _norm_str(r.get("user_id")) == user_id]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    return max(
        candidates,
        key=lambda r: _asset_criticality_rank(_norm_str(r.get("asset_id")), assets),
    )


def _pick_relationship_for_asset(
    asset_id: str,
    relationships: List[Dict[str, Any]],
    users: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    candidates = [r for r in relationships if _norm_str(r.get("asset_id")) == asset_id]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    return max(
        candidates,
        key=lambda r: _user_risk_rank(_norm_str(r.get("user_id")), users),
    )


def _apply_relationships(
    *,
    resolved_user: Optional[str],
    resolved_asset: Optional[str],
    relationships: List[Dict[str, Any]],
    users: List[Dict[str, Any]],
    assets: List[Dict[str, Any]],
) -> Tuple[Optional[str], Optional[str], List[str], List[str]]:
    matched_rels: List[str] = []
    notes: List[str] = []
    if resolved_user and resolved_asset:
        return resolved_user, resolved_asset, notes, matched_rels

    if resolved_user and resolved_asset is None:
        rel = _pick_relationship_for_user(resolved_user, relationships, assets)
        if rel:
            aid = _norm_str(rel.get("asset_id"))
            if aid:
                resolved_asset = aid
                rid = _norm_str(rel.get("relationship_id"))
                if rid:
                    matched_rels.append(rid)
                notes.append("Linked asset via relationship for user {0}".format(resolved_user))
        return resolved_user, resolved_asset, notes, matched_rels

    if resolved_asset and resolved_user is None:
        rel = _pick_relationship_for_asset(resolved_asset, relationships, users)
        if rel:
            uid = _norm_str(rel.get("user_id"))
            if uid:
                resolved_user = uid
                rid = _norm_str(rel.get("relationship_id"))
                if rid:
                    matched_rels.append(rid)
                notes.append("Linked user via relationship for asset {0}".format(resolved_asset))
        return resolved_user, resolved_asset, notes, matched_rels

    return resolved_user, resolved_asset, notes, matched_rels


def enrich_from_inventory(
    normalized: Dict[str, Any],
    users: List[Dict[str, Any]],
    assets: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
) -> EnrichmentResult:
    """Resolve user/asset from alert fields, then fill gaps using relationships."""
    asset_id, asset_conf, asset_notes = _match_assets(normalized, assets)
    user_id, user_conf, user_notes = _match_users(normalized, users)

    notes_parts = asset_notes + user_notes
    order = {"high": 3, "medium": 2, "low": 1}
    conf = "low"
    for c in (asset_conf, user_conf):
        if order.get(c, 0) > order.get(conf, 0):
            conf = c

    user_id, asset_id, rel_notes, matched_rels = _apply_relationships(
        resolved_user=user_id,
        resolved_asset=asset_id,
        relationships=relationships,
        users=users,
        assets=assets,
    )
    notes_parts.extend(rel_notes)
    if matched_rels and conf == "high":
        conf = "medium"

    if asset_id is None and user_id is None:
        return EnrichmentResult(
            resolved_asset_id=None,
            resolved_user_id=None,
            confidence="low",
            notes="No inventory match; add users/assets or map them under Relationships.",
            matched_relationship_ids=[],
        )

    summary = "; ".join(notes_parts) if notes_parts else "Inventory enrichment applied."
    return EnrichmentResult(
        resolved_asset_id=asset_id,
        resolved_user_id=user_id,
        confidence=conf if conf in ("high", "medium", "low") else "medium",
        notes=summary,
        matched_relationship_ids=matched_rels,
    )


def redact_internal_fields(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop Splunk multivalue helper keys (__mv_*) from inventory rows if present."""
    out: List[Dict[str, Any]] = []
    for row in rows:
        clean = {k: v for k, v in row.items() if not str(k).startswith("__mv_")}
        out.append(clean)
    return out
