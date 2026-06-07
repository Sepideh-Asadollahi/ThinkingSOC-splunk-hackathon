"""Entity resolution helpers for observability pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from models.enrichment import EnrichmentResult
from models.observability import EntityResolution
from services.soc_analysis.soc_analysis_risk import find_asset_row


def _norm(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _find_asset_by_host_or_ip(assets: List[Dict[str, Any]], host: str) -> Optional[Dict[str, Any]]:
    host_l = host.lower()
    for row in assets:
        if _norm(row.get("hostname")).lower() == host_l:
            return row
        if _norm(row.get("ip")).lower() == host_l:
            return row
    return None


def build_entity_resolution(
    normalized: Dict[str, Any],
    enrichment: EnrichmentResult,
    assets: List[Dict[str, Any]],
) -> Tuple[EntityResolution, Optional[Dict[str, Any]]]:
    host = _norm(normalized.get("host")) or None
    service = _norm(normalized.get("service")) or None

    asset_row = find_asset_row(assets, enrichment.resolved_asset_id)
    if asset_row is None and host:
        asset_row = _find_asset_by_host_or_ip(assets, host)

    if asset_row:
        resolved_host = _norm(asset_row.get("hostname")) or host
        return (
            EntityResolution(
                resolved_host=resolved_host or None,
                resolved_service=service,
                resolved_asset_id=_norm(asset_row.get("asset_id")) or None,
                confidence=enrichment.confidence if enrichment.confidence in ("high", "medium") else "medium",
                notes="Resolved via inventory enrichment.",
            ),
            asset_row,
        )

    return (
        EntityResolution(
            resolved_host=host,
            resolved_service=service,
            resolved_asset_id=None,
            confidence="low",
            notes="No inventory match found for host/service in this alert.",
        ),
        None,
    )
