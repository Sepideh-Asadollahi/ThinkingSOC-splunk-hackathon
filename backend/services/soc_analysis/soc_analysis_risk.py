"""Risk narrative and inventory row lookup for SOC analysis."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.enrichment import EnrichmentResult


def find_user_row(users: List[Dict[str, Any]], user_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not user_id:
        return None
    uid = str(user_id).strip()
    for row in users:
        if str(row.get("user_id", "")).strip() == uid:
            return row
    return None


def find_asset_row(assets: List[Dict[str, Any]], asset_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not asset_id:
        return None
    aid = str(asset_id).strip()
    for row in assets:
        if str(row.get("asset_id", "")).strip() == aid:
            return row
    return None


def build_risk_context(
    enrichment: EnrichmentResult,
    user_row: Optional[Dict[str, Any]],
    asset_row: Optional[Dict[str, Any]],
) -> str:
    parts: List[str] = []
    if asset_row:
        parts.append(
            "Asset {0}: criticality={1}, risk_score={2}.".format(
                asset_row.get("asset_id", ""),
                asset_row.get("criticality", "unknown"),
                asset_row.get("risk_score", "unknown"),
            )
        )
    elif enrichment.resolved_asset_id:
        parts.append(
            "Asset id {0} was resolved but full inventory row was not found.".format(enrichment.resolved_asset_id)
        )
    if user_row:
        parts.append(
            "User {0}: risk_score={1}, department={2}.".format(
                user_row.get("user_id", ""),
                user_row.get("risk_score", "unknown"),
                user_row.get("department") or "n/a",
            )
        )
    elif enrichment.resolved_user_id:
        parts.append(
            "User id {0} was resolved but full inventory row was not found.".format(enrichment.resolved_user_id)
        )
    if not parts:
        parts.append(
            "No confident link to organizational inventory; treat asset/user risk as unknown. {0}".format(
                enrichment.notes
            )
        )
    return " ".join(parts)
