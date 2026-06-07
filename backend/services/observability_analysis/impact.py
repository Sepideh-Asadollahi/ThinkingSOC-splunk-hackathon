"""Impact context builder for observability pipeline."""

from __future__ import annotations

from typing import Any, Dict, Optional

from models.observability import EntityResolution, ImpactContext


def _to_float(v: Any) -> Optional[float]:
    try:
        if v is None or str(v).strip() == "":
            return None
        return float(v)
    except Exception:
        return None


def _severity_score(v: str) -> int:
    return {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(v.lower(), 0)


def build_impact_context(
    normalized: Dict[str, Any],
    entity: EntityResolution,
    asset_row: Optional[Dict[str, Any]],
) -> ImpactContext:
    score = 0
    sev = str(normalized.get("severity") or "").strip().lower()
    score += _severity_score(sev)

    criticality = str((asset_row or {}).get("criticality") or "unknown").strip().lower()
    score += _severity_score(criticality)

    cpu = _to_float(normalized.get("cpu"))
    mem = _to_float(normalized.get("memory"))
    disk = _to_float(normalized.get("disk"))
    latency = _to_float(normalized.get("latency_ms"))
    err = _to_float(normalized.get("error_rate"))

    if cpu is not None and cpu >= 90:
        score += 2
    if mem is not None and mem >= 90:
        score += 2
    if disk is not None and disk >= 90:
        score += 2
    if latency is not None and latency >= 1000:
        score += 2
    if err is not None and err >= 2:
        score += 2

    if score >= 8:
        level = "critical"
    elif score >= 6:
        level = "high"
    elif score >= 3:
        level = "medium"
    else:
        level = "low"

    entities = [e for e in [entity.resolved_host, entity.resolved_service] if e]
    customer_impact = "Possible service degradation is affecting end-user requests."
    if level in ("low", "medium"):
        customer_impact = "Potential localized service impact; monitor closely."

    return ImpactContext(
        impact_level=level,
        affected_entities=entities,
        customer_impact=customer_impact,
        business_criticality=criticality if criticality else "unknown",
        time_window="around alert window",
    )
