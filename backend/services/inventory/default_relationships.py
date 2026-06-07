"""Infer default user–asset relationships from inventory rows."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

# Demo/hackathon: asset.owner team label → user.department for auto-linking.
_OWNER_TEAM_TO_DEPARTMENT: Mapping[str, str] = {
    "ops": "IT",
    "dba": "Finance",
}


def _norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _relationship_id(user_id: str, asset_id: str) -> str:
    base = "rel-{0}-{1}".format(user_id, asset_id)
    return base.replace(" ", "-")[:120]


def _pick_user_for_asset(
    asset: Dict[str, Any],
    users: List[Dict[str, Any]],
    users_by_id: Dict[str, Dict[str, Any]],
    users_by_department: Dict[str, List[Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    owner = _norm(asset.get("owner")).lower()
    if not owner:
        return None

    if owner in users_by_id:
        return users_by_id[owner]

    dept_label = _OWNER_TEAM_TO_DEPARTMENT.get(owner)
    if not dept_label:
        return None

    dept_key = dept_label.lower()
    candidates = users_by_department.get(dept_key, [])
    if not candidates:
        return None
    return sorted(candidates, key=lambda u: _norm(u.get("user_id")))[0]


def build_default_relationships(
    users: List[Dict[str, Any]],
    assets: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build relationship dicts from inventory only.

    Rules (first match wins per asset):
    1. ``asset.owner`` equals ``user.user_id`` (case-insensitive).
    2. ``asset.owner`` is a known team label mapped to ``user.department``
       (demo: ``ops`` → IT, ``dba`` → Finance); one user per department.
    """
    users_by_id = {_norm(u.get("user_id")).lower(): u for u in users if _norm(u.get("user_id"))}
    users_by_department: Dict[str, List[Dict[str, Any]]] = {}
    for user in users:
        dept = _norm(user.get("department")).lower()
        if dept:
            users_by_department.setdefault(dept, []).append(user)

    out: List[Dict[str, Any]] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    for asset in assets:
        asset_id = _norm(asset.get("asset_id"))
        if not asset_id:
            continue
        user = _pick_user_for_asset(asset, users, users_by_id, users_by_department)
        if user is None:
            continue
        user_id = _norm(user.get("user_id"))
        pair = (user_id, asset_id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        owner = _norm(asset.get("owner"))
        out.append(
            {
                "relationship_id": _relationship_id(user_id, asset_id),
                "user_id": user_id,
                "asset_id": asset_id,
                "description": "Auto-linked from inventory (asset owner: {0})".format(owner or "—"),
            }
        )
    return out


def merge_relationship_lists(
    explicit: List[Dict[str, Any]],
    defaults: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge by (user_id, asset_id); explicit rows override generated defaults."""
    by_pair: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for rel in defaults:
        uid, aid = _norm(rel.get("user_id")), _norm(rel.get("asset_id"))
        if uid and aid:
            by_pair[(uid, aid)] = rel
    for rel in explicit:
        uid, aid = _norm(rel.get("user_id")), _norm(rel.get("asset_id"))
        if uid and aid:
            by_pair[(uid, aid)] = rel
    return list(by_pair.values())
