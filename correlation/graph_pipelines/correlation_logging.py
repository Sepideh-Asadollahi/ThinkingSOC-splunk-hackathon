"""Structured INFO logs for Attack Discovery correlation (grep: correlation.discovery)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("correlation.discovery")


def log_step(step: str, **fields: Any) -> None:
    parts = [f"step={step}"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, (dict, list, set)):
            parts.append(f"{key}={json.dumps(value, ensure_ascii=False, default=str)}")
        else:
            parts.append(f"{key}={value}")
    logger.info("correlation %s", " ".join(parts))


def format_timestamp(alert: dict[str, Any]) -> str:
    ts = alert.get("timestamp")
    if ts is None:
        return "no-ts"
    if hasattr(ts, "to_native"):
        ts = ts.to_native()
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.isoformat()
    return str(ts)


def format_alert_line(alert: dict[str, Any]) -> str:
    aid = alert.get("alert_row_id") or "?"
    name = (str(alert.get("name") or ""))[:48]
    risk = int(alert.get("risk_score") or 0)
    status = alert.get("status") or "?"
    ents = alert.get("entity_identifiers") or []
    ent_short = ",".join(str(e) for e in ents[:4])
    if len(ents) > 4:
        ent_short += f",+{len(ents) - 4}"
    return (
        f"{aid}|risk={risk}|status={status}|ts={format_timestamp(alert)}"
        f"|name={name!r}|entities=[{ent_short}]"
    )


def format_cluster(cluster: dict[str, Any], index: int | None = None) -> dict[str, Any]:
    alerts = cluster.get("alerts") or []
    ids = [str(a.get("alert_row_id")) for a in alerts if a.get("alert_row_id")]
    entities: set[str] = set()
    for a in alerts:
        entities.update(str(e) for e in (a.get("entity_identifiers") or []) if e)
    prefix = f"cluster_{index}" if index is not None else "cluster"
    return {
        f"{prefix}_size": len(alerts),
        f"{prefix}_alert_ids": ids,
        f"{prefix}_entities": sorted(entities),
    }


def log_clusters(phase: str, clusters: list[dict[str, Any]], *, window_hours: int | None = None) -> None:
    fields: dict[str, Any] = {"phase": phase, "cluster_count": len(clusters)}
    if window_hours is not None:
        fields["window_hours"] = window_hours
    for i, cluster in enumerate(clusters):
        fields.update(format_cluster(cluster, i))
        alerts = cluster.get("alerts") or []
        fields[f"cluster_{i}_alerts"] = [format_alert_line(a) for a in alerts]
    log_step("clusters", **fields)
