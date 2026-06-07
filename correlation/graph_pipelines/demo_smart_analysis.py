from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

from correlation_config import get_settings
from graph_core.operation_store import operation_store
from graph_core.entity_taxonomy import (
    is_asset_anchor,
    is_identity_anchor,
    is_indicator_entity,
)
from graph_crud.correlation import find_historical_related_incidents, load_alerts_from_neo4j
from graph_crud.schema import seed_demo_data_if_empty
from graph_crud.findings import find_by_content_hash, insert_finding
from graph_crud.incident_sync import sync_finding_incident_to_neo4j
from graph_pipelines.attack_alert_filter import (
    average_alert_risk,
    is_attack_indicative,
    prepare_attack_clusters,
    sort_alerts_by_time,
)
from graph_pipelines.correlation_logging import format_alert_line, log_step
from graph_pipelines.llm_stub import (
    correlate_clusters,
    generate_smart_finding_report,
    merge_cluster_alerts,
    partition_clusters_by_merge,
)


def _cluster_attack_alerts(cluster: dict[str, Any]) -> dict[str, Any]:
    before = [str(a.get("alert_row_id")) for a in cluster.get("alerts") or []]
    alerts = [a for a in (cluster.get("alerts") or []) if is_attack_indicative(a)]
    if not alerts:
        alerts = list(cluster.get("alerts") or [])
        log_step("cluster_attack_filter", action="kept_all_fallback", before_ids=before)
    else:
        after = [str(a.get("alert_row_id")) for a in alerts]
        if before != after:
            log_step("cluster_attack_filter", before_ids=before, after_ids=after)
    return {"alerts": alerts}


def _build_details(
    cluster: dict[str, Any],
    report: dict[str, Any],
    historical: list[dict[str, Any]],
    merge_result: dict[str, Any],
) -> dict[str, Any]:
    alerts = sort_alerts_by_time(cluster.get("alerts") or [])
    contributing = []
    identities: set[str] = set()
    assets: set[str] = set()
    iocs: set[str] = set()
    for a in alerts:
        for entity in a.get("entity_identifiers") or []:
            eid = str(entity)
            if is_identity_anchor(eid):
                identities.add(eid)
            elif is_asset_anchor(eid):
                assets.add(eid)
            elif is_indicator_entity(eid):
                iocs.add(eid)
        contributing.append(
            {
                "alert_row_id": a.get("alert_row_id"),
                "alert_name": a.get("search_name") or a.get("name"),
                "sid": a.get("sid"),
                "search_name": a.get("search_name") or a.get("name"),
                "timestamp": str(a.get("timestamp", "")),
                "threat_status": a.get("status", "open"),
                "risk_score": int(a.get("risk_score") or 0),
            }
        )

    return {
        "incident_id": f"incident-{hashlib.md5(json.dumps([a.get('alert_row_id') for a in alerts], sort_keys=True).encode()).hexdigest()[:8]}",
        "incident_title": report.get("title", "Automated cluster"),
        "executive_summary": report.get("executive_summary", report.get("summary", "")),
        "attack_analysis_steps": report.get("attack_analysis_steps", []),
        "attack_timeline_trees": report.get("attack_timeline_trees", []),
        "key_entities": {
            "identities": sorted(identities),
            "assets": sorted(assets),
            "iocs": sorted(iocs),
        },
        "contributing_alerts": contributing,
        "framework_mappings": [],
        "historical_related_incidents": historical,
        "recommended_next_steps": ["Review correlated alerts", "Validate entity overlap"],
        "smart_hunt_queries": [],
        "aggregated_mitre_techniques": [],
        "raw_analysis": {"cluster_merge": merge_result},
        "raw_paths": [],
    }


def _content_hash(clusters: list[dict[str, Any]]) -> str:
    ids = sorted(
        str(a.get("alert_row_id"))
        for c in clusters
        for a in c.get("alerts") or []
        if a.get("alert_row_id")
    )
    return hashlib.sha256(",".join(ids).encode()).hexdigest()


async def run_demo_smart_analysis(
    operation_id: str,
    *,
    limit_to_latest_alerts: int = 50,
    force_reanalysis: bool = True,
) -> None:
    settings = get_settings()
    try:
        log_step(
            "pipeline_start",
            operation_id=operation_id,
            limit=limit_to_latest_alerts,
            force_reanalysis=force_reanalysis,
            window_hours=settings.correlation_cluster_window_hours,
            lookback_days=settings.smart_analysis_lookback_days,
        )
        if settings.tsoc_correlation_auto_seed:
            await seed_demo_data_if_empty(settings)

        await operation_store.append_log(operation_id, "Fetching alerts from Neo4j...")
        alerts = await load_alerts_from_neo4j(
            limit=limit_to_latest_alerts,
            lookback_days=settings.smart_analysis_lookback_days,
        )
        if not alerts and settings.tsoc_correlation_auto_seed:
            log_step("neo4j_empty", action="auto_seed_retry")
            await operation_store.append_log(
                operation_id,
                "Neo4j had no alerts in lookback window — reloading demo seed...",
            )
            await seed_demo_data_if_empty(settings)
            alerts = await load_alerts_from_neo4j(
                limit=limit_to_latest_alerts,
                lookback_days=settings.smart_analysis_lookback_days,
            )
        await asyncio.sleep(0.5)
        await operation_store.append_log(
            operation_id, f"Fetched {len(alerts)} alerts from Neo4j"
        )
        log_step("neo4j_load", count=len(alerts), alerts=[format_alert_line(a) for a in alerts])

        window_hours = settings.correlation_cluster_window_hours
        selected_clusters = prepare_attack_clusters(alerts, window_hours=window_hours)
        selected_clusters = [_cluster_attack_alerts(c) for c in selected_clusters]

        cluster_sizes = ", ".join(
            str(len(c.get("alerts") or [])) for c in selected_clusters
        ) or "0"
        await operation_store.append_log(
            operation_id,
            f"Selected {len(selected_clusters)} attack cluster(s) "
            f"({cluster_sizes} alerts; {window_hours}h window)...",
        )
        await asyncio.sleep(0.5)

        content_hash = _content_hash(selected_clusters)
        log_step("content_hash", hash=content_hash)
        if not force_reanalysis:
            existing = await find_by_content_hash(content_hash)
            if existing:
                log_step("dedup_hit", finding_ids=existing)
                await operation_store.complete(
                    operation_id,
                    {
                        "findings_created": 0,
                        "finding_ids": existing,
                        "smart_analysis_summary": {
                            "clusters": len(selected_clusters),
                            "merged_incidents": 0,
                            "alerts_processed": len(alerts),
                        },
                    },
                    message="Reused existing findings (dedup)",
                )
                return

        per_cluster_reports: list[dict[str, Any]] = []
        for idx, cluster in enumerate(selected_clusters):
            ids = [a.get("alert_row_id") for a in cluster.get("alerts") or []]
            await operation_store.append_log(
                operation_id, f"Generating report for cluster {idx + 1}..."
            )
            log_step("llm_report_start", cluster_index=idx, alert_ids=ids)
            report = await generate_smart_finding_report(cluster)
            log_step(
                "llm_report_done",
                cluster_index=idx,
                title=report.get("title"),
                summary=(str(report.get("summary") or ""))[:120],
            )
            per_cluster_reports.append(report)

        if len(selected_clusters) > 1:
            await operation_store.append_log(
                operation_id,
                "LLM reviewing whether clusters are one attack or separate...",
            )
        log_step("llm_merge_start", cluster_count=len(selected_clusters))
        merge_result = await correlate_clusters(selected_clusters, per_cluster_reports)
        incident_groups = partition_clusters_by_merge(len(selected_clusters), merge_result)
        log_step(
            "llm_merge_done",
            merge_result=merge_result,
            incident_groups=incident_groups,
        )

        merged_count = sum(1 for g in incident_groups if len(g) > 1)
        if merged_count:
            await operation_store.append_log(
                operation_id,
                f"Merged {merged_count} cluster group(s) into combined incident(s).",
            )
        elif len(selected_clusters) > 1:
            await operation_store.append_log(
                operation_id,
                "Clusters kept separate — distinct attack(s).",
            )

        finding_ids: list[str] = []
        merged_incidents = 0

        for group_idx, group in enumerate(incident_groups):
            merged_cluster = merge_cluster_alerts(selected_clusters, group)
            cluster_alerts = merged_cluster.get("alerts") or []
            if not cluster_alerts:
                continue

            log_step(
                "incident_group",
                group_index=group_idx,
                source_cluster_indices=group,
                alert_ids=[a.get("alert_row_id") for a in cluster_alerts],
            )

            if len(group) > 1:
                report = await generate_smart_finding_report(merged_cluster)
            else:
                report = per_cluster_reports[group[0]]

            alert_ids = [str(a.get("alert_row_id")) for a in cluster_alerts if a.get("alert_row_id")]
            await operation_store.append_log(
                operation_id, f"Historical lookup for incident {group_idx + 1}..."
            )
            historical = await find_historical_related_incidents(
                alert_ids,
                lookback_days=settings.smart_analysis_lookback_days,
            )
            log_step(
                "historical_incidents",
                group_index=group_idx,
                alert_ids=alert_ids,
                related=historical,
            )
            if historical:
                merged_incidents += len(historical)

            details = _build_details(merged_cluster, report, historical, merge_result)
            linked = await sync_finding_incident_to_neo4j(
                incident_id=str(details["incident_id"]),
                title=str(report.get("title", "Attack Discovery")),
                alert_row_ids=alert_ids,
            )
            if linked:
                await operation_store.append_log(
                    operation_id,
                    f"Linked {linked} alert(s) to Neo4j incident for Graph Explorer.",
                )
            finding_risk = average_alert_risk(cluster_alerts)
            fid = await insert_finding(
                title=str(report.get("title", "Attack Discovery")),
                summary=str(report.get("summary", "")),
                details=details,
                risk_score=finding_risk,
                content_hash=content_hash if group_idx == 0 else None,
            )
            log_step(
                "finding_inserted",
                finding_id=fid,
                incident_id=details["incident_id"],
                title=report.get("title"),
                risk_score=finding_risk,
                contributing_count=len(details.get("contributing_alerts") or []),
            )
            finding_ids.append(fid)
            await asyncio.sleep(0.5)

        if not finding_ids:
            message = "Attack Discovery found no reportable attack clusters"
            log_step(
                "pipeline_empty",
                operation_id=operation_id,
                alerts_loaded=len(alerts),
                clusters=len(selected_clusters),
            )
            await operation_store.fail(operation_id, message)
            return

        log_step(
            "pipeline_complete",
            operation_id=operation_id,
            findings_created=len(finding_ids),
            finding_ids=finding_ids,
        )
        await operation_store.complete(
            operation_id,
            {
                "findings_created": len(finding_ids),
                "finding_ids": finding_ids,
                "smart_analysis_summary": {
                    "clusters": len(selected_clusters),
                    "incidents": len(incident_groups),
                    "merged_cluster_groups": merged_count,
                    "merged_incidents": merged_incidents,
                    "alerts_processed": len(alerts),
                    "cluster_merge": merge_result,
                },
            },
            message="Smart analysis completed",
        )
    except Exception as exc:
        log_step("pipeline_fail", operation_id=operation_id, error=str(exc))
        await operation_store.fail(operation_id, str(exc))
