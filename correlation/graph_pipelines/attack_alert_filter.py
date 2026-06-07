from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from graph_core.entity_taxonomy import (
    anchor_entities_on_alert,
    cluster_has_anchor,
    cluster_is_indicator_only_singleton,
    clusters_share_anchor_entities,
    is_indicator_only_alert,
    primary_anchor_display,
)
from graph_pipelines.correlation_logging import (
    format_alert_line,
    format_cluster,
    log_clusters,
    log_step,
)

_ATTACK_KEYWORDS = (
    "phish",
    "malicious",
    "malware",
    "ransomware",
    "c2",
    "beacon",
    "lateral",
    "psexec",
    "rdp",
    "powershell",
    "suspicious",
    "exploit",
    "credential",
    "brute",
    "exfil",
    "command and control",
    "scheduled task",
    "download activity",
    "tunnel",
    "backdoor",
    "trojan",
    "persistence",
    "privilege",
    "unusual login",
    "outbound",
    "compromise",
    "kill chain",
    "initial access",
)

_NOISE_KEYWORDS = (
    "informational",
    "audit log",
    "heartbeat",
    "health check",
)

def _alert_timestamp(alert: dict[str, Any]) -> datetime | None:
    ts = alert.get("timestamp")
    if ts is None:
        return None
    if hasattr(ts, "to_native"):
        ts = ts.to_native()
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _campaign_entities(alert: dict[str, Any]) -> set[str]:
    """Anchor entities (user/host/asset) used for campaign enrichment and merge policy."""
    return anchor_entities_on_alert(alert)


def _cluster_campaign_entities(cluster: dict[str, Any]) -> set[str]:
    entities: set[str] = set()
    for alert in cluster.get("alerts") or []:
        entities.update(_campaign_entities(alert))
    return entities


def _cluster_time_bounds(alerts: list[dict[str, Any]]) -> tuple[datetime | None, datetime | None]:
    times = [_alert_timestamp(a) for a in alerts]
    valid = [t for t in times if t is not None]
    if not valid:
        return None, None
    return min(valid), max(valid)


def _within_hours(ts: datetime, start: datetime, end: datetime, padding_hours: int) -> bool:
    pad = padding_hours * 3600
    return (start.timestamp() - pad) <= ts.timestamp() <= (end.timestamp() + pad)


def is_attack_indicative(alert: dict[str, Any]) -> bool:
    """True when an alert plausibly indicates malicious activity (not general noise)."""
    name = str(alert.get("name") or "").lower()
    risk = int(alert.get("risk_score") or 0)
    status = str(alert.get("status") or "").lower()

    if any(noise in name for noise in _NOISE_KEYWORDS) and risk < 50:
        return False

    if risk >= 55:
        return True

    if any(kw in name for kw in _ATTACK_KEYWORDS):
        return True

    entities = alert.get("entity_identifiers") or []
    if entities and risk >= 45 and status != "closed":
        return True

    if status == "closed" and risk >= 50 and any(kw in name for kw in _ATTACK_KEYWORDS):
        return True

    return False


def explain_attack_indicative(alert: dict[str, Any]) -> tuple[bool, str]:
    """Human-readable reason for attack-indicative filter (for logs)."""
    name = str(alert.get("name") or "").lower()
    risk = int(alert.get("risk_score") or 0)
    status = str(alert.get("status") or "").lower()
    entities = alert.get("entity_identifiers") or []

    if any(noise in name for noise in _NOISE_KEYWORDS) and risk < 50:
        return False, "noise_keyword_low_risk"
    if risk >= 55:
        return True, f"risk>={55}"
    if any(kw in name for kw in _ATTACK_KEYWORDS):
        matched = next(kw for kw in _ATTACK_KEYWORDS if kw in name)
        return True, f"keyword:{matched}"
    if entities and risk >= 45 and status != "closed":
        return True, f"entities_risk>={45}_open"
    if status == "closed" and risk >= 50 and any(kw in name for kw in _ATTACK_KEYWORDS):
        matched = next(kw for kw in _ATTACK_KEYWORDS if kw in name)
        return True, f"closed_attack_keyword:{matched}"
    return False, "below_threshold"


def filter_attack_alerts(
    alerts: list[dict[str, Any]],
    *,
    log_decisions: bool = True,
) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for alert in alerts:
        ok, reason = explain_attack_indicative(alert)
        if log_decisions:
            log_step(
                "filter_attack",
                alert_row_id=alert.get("alert_row_id"),
                keep=ok,
                reason=reason,
                line=format_alert_line(alert),
            )
        if ok:
            kept.append(alert)
    if log_decisions:
        log_step(
            "filter_attack_summary",
            input_count=len(alerts),
            kept_count=len(kept),
            dropped_count=len(alerts) - len(kept),
        )
    return kept


def group_alerts_by_shared_entity(
    alerts: list[dict[str, Any]],
    *,
    window_hours: int = 168,
    log_decisions: bool = True,
) -> list[dict[str, Any]]:
    """Cluster alerts that share Identity/Asset/IOC identifiers within a time window."""
    if not alerts:
        return []

    if log_decisions:
        log_step("group_entity_start", input_count=len(alerts), window_hours=window_hours)

    alert_by_id: dict[str, dict[str, Any]] = {}
    for alert in alerts:
        aid = str(alert.get("alert_row_id") or "")
        if aid:
            alert_by_id[aid] = alert

    alert_ids = list(alert_by_id.keys())
    if not alert_ids:
        return []

    entity_to_alerts: dict[str, list[str]] = defaultdict(list)
    for aid, alert in alert_by_id.items():
        for entity in alert.get("entity_identifiers") or []:
            entity_to_alerts[str(entity)].append(aid)

    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    max_delta = window_hours * 3600
    unions: list[dict[str, Any]] = []
    for entity, members in entity_to_alerts.items():
        if len(members) < 2:
            continue
        anchor = members[0]
        for other in members[1:]:
            a = alert_by_id[anchor]
            b = alert_by_id[other]
            ts_a = _alert_timestamp(a)
            ts_b = _alert_timestamp(b)
            delta_s: float | None = None
            if ts_a and ts_b:
                delta_s = abs((ts_a - ts_b).total_seconds())
                if delta_s > max_delta:
                    if log_decisions:
                        log_step(
                            "group_entity_skip",
                            entity=entity,
                            alert_a=anchor,
                            alert_b=other,
                            delta_hours=round(delta_s / 3600, 2),
                            max_hours=window_hours,
                            reason="outside_time_window",
                        )
                    continue
            union(anchor, other)
            if log_decisions:
                unions.append(
                    {
                        "entity": entity,
                        "alert_a": anchor,
                        "alert_b": other,
                        "delta_hours": round(delta_s / 3600, 2) if delta_s is not None else None,
                    }
                )

    clusters_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for aid in alert_ids:
        root = find(aid)
        clusters_map[root].append(alert_by_id[aid])

    clusters = [{"alerts": _sort_alerts_by_time(cluster_alerts)} for cluster_alerts in clusters_map.values()]
    if log_decisions:
        log_step("group_entity_unions", union_count=len(unions), unions=unions)
        log_clusters("group_entity_result", clusters, window_hours=window_hours)
    return clusters


def sort_alerts_by_time(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return alerts sorted chronologically (earliest first)."""
    return sorted(alerts, key=lambda a: _alert_timestamp(a) or datetime.min.replace(tzinfo=timezone.utc))


_sort_alerts_by_time = sort_alerts_by_time


def enrich_clusters_with_related_alerts(
    clusters: list[dict[str, Any]],
    pool: list[dict[str, Any]],
    *,
    window_hours: int = 168,
    log_decisions: bool = True,
) -> list[dict[str, Any]]:
    """Attach attack alerts that share user/host with a cluster within the campaign window."""
    pool_by_id = {str(a.get("alert_row_id")): a for a in pool if a.get("alert_row_id")}
    enriched: list[dict[str, Any]] = []

    for idx, cluster in enumerate(clusters):
        alerts = list(cluster.get("alerts") or [])
        before_ids = [str(a.get("alert_row_id")) for a in alerts]
        seen = {str(a.get("alert_row_id")) for a in alerts if a.get("alert_row_id")}
        campaign = _cluster_campaign_entities(cluster)
        t_min, t_max = _cluster_time_bounds(alerts)
        attached: list[dict[str, Any]] = []

        if campaign and t_min and t_max:
            for aid, candidate in pool_by_id.items():
                if aid in seen:
                    continue
                if not is_attack_indicative(candidate):
                    if log_decisions:
                        log_step(
                            "enrich_skip",
                            cluster_index=idx,
                            alert_row_id=aid,
                            reason="not_attack_indicative",
                        )
                    continue
                overlap = _campaign_entities(candidate) & campaign
                if not overlap:
                    continue
                ts = _alert_timestamp(candidate)
                if ts and not _within_hours(ts, t_min, t_max, window_hours):
                    if log_decisions:
                        log_step(
                            "enrich_skip",
                            cluster_index=idx,
                            alert_row_id=aid,
                            reason="outside_campaign_window",
                            shared_entities=sorted(overlap),
                            cluster_t_min=str(t_min),
                            cluster_t_max=str(t_max),
                        )
                    continue
                alerts.append(candidate)
                seen.add(aid)
                attached.append({"alert_row_id": aid, "shared_entities": sorted(overlap)})

        if log_decisions:
            log_step(
                "enrich_cluster",
                cluster_index=idx,
                campaign_entities=sorted(campaign),
                before_ids=before_ids,
                attached=attached,
                after_ids=[str(a.get("alert_row_id")) for a in alerts],
            )
        enriched.append({"alerts": _sort_alerts_by_time(alerts)})

    if log_decisions:
        log_clusters("enrich_result", enriched, window_hours=window_hours)
    return enriched


def merge_clusters_by_campaign_identity(
    clusters: list[dict[str, Any]],
    *,
    window_hours: int = 168,
    log_decisions: bool = True,
) -> list[dict[str, Any]]:
    """Merge clusters that share username/host and overlap in time (same victim campaign)."""
    if len(clusters) < 2:
        return clusters

    if log_decisions:
        log_clusters("merge_campaign_start", clusters, window_hours=window_hours)

    parent = list(range(len(clusters)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    bounds = [_cluster_time_bounds(c.get("alerts") or []) for c in clusters]
    campaign_sets = [_cluster_campaign_entities(c) for c in clusters]

    max_gap = window_hours * 3600
    merge_pairs: list[dict[str, Any]] = []
    for i in range(len(clusters)):
        for j in range(i + 1, len(clusters)):
            shared = campaign_sets[i] & campaign_sets[j]
            if not shared:
                continue
            t_min_i, t_max_i = bounds[i]
            t_min_j, t_max_j = bounds[j]
            if not all([t_min_i, t_max_i, t_min_j, t_max_j]):
                union(i, j)
                merge_pairs.append(
                    {"cluster_a": i, "cluster_b": j, "shared": sorted(shared), "reason": "missing_timestamps"}
                )
                continue
            gap_seconds = max(
                0.0,
                (max(t_min_i, t_min_j) - min(t_max_i, t_max_j)).total_seconds(),  # type: ignore[arg-type]
            )
            if gap_seconds <= max_gap:
                union(i, j)
                merge_pairs.append(
                    {
                        "cluster_a": i,
                        "cluster_b": j,
                        "shared": sorted(shared),
                        "gap_hours": round(gap_seconds / 3600, 2),
                    }
                )
            elif log_decisions:
                log_step(
                    "merge_campaign_skip",
                    cluster_a=i,
                    cluster_b=j,
                    shared_entities=sorted(shared),
                    gap_hours=round(gap_seconds / 3600, 2),
                    max_gap_hours=window_hours,
                )

    if log_decisions:
        log_step("merge_campaign_pairs", pairs=merge_pairs)

    groups: dict[int, list[int]] = defaultdict(list)
    for idx in range(len(clusters)):
        groups[find(idx)].append(idx)

    merged: list[dict[str, Any]] = []
    for indices in groups.values():
        alerts: list[dict[str, Any]] = []
        seen: set[str] = set()
        for idx in indices:
            for alert in clusters[idx].get("alerts") or []:
                aid = str(alert.get("alert_row_id") or "")
                if aid and aid in seen:
                    continue
                if aid:
                    seen.add(aid)
                alerts.append(alert)
        merged.append({"alerts": _sort_alerts_by_time(alerts)})

    if log_decisions:
        log_clusters("merge_campaign_result", merged, window_hours=window_hours)
    return merged


def merge_blocked_by_indicator_split(
    cluster_a: dict[str, Any],
    cluster_b: dict[str, Any],
) -> bool:
    """Block re-merge of indicator-only singletons into anchor-based kill chains."""
    indicator_singleton = cluster_is_indicator_only_singleton(
        cluster_a
    ) or cluster_is_indicator_only_singleton(cluster_b)
    if not indicator_singleton:
        return False
    if not (cluster_has_anchor(cluster_a) or cluster_has_anchor(cluster_b)):
        return False
    return not clusters_share_anchor_entities(cluster_a, cluster_b)


# Back-compat alias for merge guard tests/imports
merge_blocked_by_ioc_split = merge_blocked_by_indicator_split


def apply_indicator_split_merge_guard(
    clusters: list[dict[str, Any]],
    merge_result: dict[str, Any],
) -> dict[str, Any]:
    """Drop LLM/heuristic merge groups that undo ``split_indicator_only_from_anchor_clusters``."""
    filtered_groups: list[list[int]] = []
    for group in merge_result.get("merge_groups") or []:
        if not isinstance(group, list) or len(group) < 2:
            continue
        blocked = False
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = int(group[i]), int(group[j])
                if not (0 <= a < len(clusters) and 0 <= b < len(clusters)):
                    continue
                if merge_blocked_by_indicator_split(clusters[a], clusters[b]):
                    log_step(
                        "llm_merge_blocked",
                        cluster_indices=[a, b],
                        reason="indicator_split_policy",
                    )
                    blocked = True
                    break
            if blocked:
                break
        if not blocked:
            filtered_groups.append(sorted(int(x) for x in group))

    out = dict(merge_result)
    out["merge_groups"] = filtered_groups
    if filtered_groups != merge_result.get("merge_groups"):
        out["reasoning"] = (
            str(merge_result.get("reasoning") or "")
            + " (Indicator-only cluster kept separate from anchor-based campaign.)"
        ).strip()
    return out


apply_ioc_split_merge_guard = apply_indicator_split_merge_guard


def split_indicator_only_from_anchor_clusters(
    clusters: list[dict[str, Any]],
    *,
    log_decisions: bool = True,
) -> list[dict[str, Any]]:
    """Pull indicator-only alerts out of clusters that also have anchor entities (user/host/asset)."""
    out: list[dict[str, Any]] = []
    for idx, cluster in enumerate(clusters):
        alerts = cluster.get("alerts") or []
        has_anchor_in_cluster = cluster_has_anchor(cluster)
        anchored: list[dict[str, Any]] = []
        indicator_only: list[dict[str, Any]] = []
        for alert in alerts:
            ents = [str(e) for e in (alert.get("entity_identifiers") or []) if e]
            if is_indicator_only_alert(alert) and has_anchor_in_cluster:
                indicator_only.append(alert)
                if log_decisions:
                    log_step(
                        "split_indicator_out",
                        cluster_index=idx,
                        alert_row_id=alert.get("alert_row_id"),
                        entities=ents,
                        reason="indicator_only_in_anchor_campaign",
                    )
            else:
                anchored.append(alert)
        if anchored:
            out.append({"alerts": _sort_alerts_by_time(anchored)})
        for alert in indicator_only:
            out.append({"alerts": [alert]})
    result = out if out else clusters
    if log_decisions:
        log_clusters("split_indicator_result", result)
    return result


split_ioc_only_from_host_clusters = split_indicator_only_from_anchor_clusters


def explain_cluster_score(cluster: dict[str, Any]) -> dict[str, Any]:
    alerts = cluster.get("alerts") or []
    if not alerts:
        return {"score": 0.0, "parts": {}}

    max_risk = max(int(a.get("risk_score") or 0) for a in alerts)
    open_count = sum(1 for a in alerts if str(a.get("status") or "").lower() != "closed")
    shared_entities: set[str] = set()
    for alert in alerts:
        shared_entities.update(str(e) for e in (alert.get("entity_identifiers") or []) if e)

    parts = {
        "max_risk": float(max_risk),
        "alert_count_x8": len(alerts) * 8.0,
        "open_count_x5": open_count * 5.0,
        "entities_x3": min(len(shared_entities), 6) * 3.0,
    }
    newest = max(
        (_alert_timestamp(a) for a in alerts if _alert_timestamp(a) is not None),
        default=None,
    )
    if newest is not None:
        age_hours = (datetime.now(timezone.utc) - newest).total_seconds() / 3600.0
        parts["recency_bonus"] = max(0.0, 48.0 - age_hours) * 0.5
        parts["newest_age_hours"] = round(age_hours, 2)

    score = (
        parts["max_risk"]
        + parts["alert_count_x8"]
        + parts["open_count_x5"]
        + parts["entities_x3"]
        + parts.get("recency_bonus", 0.0)
    )
    return {"score": score, "parts": parts}


def explain_cluster_meaningful(cluster: dict[str, Any]) -> tuple[bool, str]:
    alerts = cluster.get("alerts") or []
    if len(alerts) >= 2:
        entity_sets = [set(a.get("entity_identifiers") or []) for a in alerts]
        shared = set.intersection(*entity_sets) if entity_sets else set()
        if shared:
            return True, f"multi_alert_shared_entities:{sorted(shared)}"
        if _cluster_campaign_entities(cluster):
            return True, f"multi_alert_campaign_entities:{sorted(_cluster_campaign_entities(cluster))}"
        max_risk = max(int(a.get("risk_score") or 0) for a in alerts)
        if max_risk >= 70:
            return True, f"multi_alert_max_risk>={70}"
        return False, f"multi_alert_max_risk={max_risk}<70"
    if len(alerts) == 1:
        a = alerts[0]
        risk = int(a.get("risk_score") or 0)
        if is_attack_indicative(a) and risk >= 55:
            return True, f"singleton_risk>={55}"
        return False, f"singleton_risk={risk}<55_or_not_indicative"
    return False, "empty_cluster"


def prepare_attack_clusters(
    all_alerts: list[dict[str, Any]],
    *,
    window_hours: int = 168,
    log_decisions: bool = True,
) -> list[dict[str, Any]]:
    """Filter, cluster, enrich, and select attack clusters for Attack Discovery."""
    if log_decisions:
        log_step(
            "prepare_start",
            total_alerts=len(all_alerts),
            window_hours=window_hours,
            alert_lines=[format_alert_line(a) for a in all_alerts],
        )

    attack_alerts = filter_attack_alerts(all_alerts, log_decisions=log_decisions)
    source = attack_alerts if attack_alerts else all_alerts
    if log_decisions and not attack_alerts:
        log_step("prepare_fallback", reason="no_attack_indicative_using_all", count=len(all_alerts))

    clusters = group_alerts_by_shared_entity(source, window_hours=window_hours, log_decisions=log_decisions)
    clusters = enrich_clusters_with_related_alerts(
        clusters, source, window_hours=window_hours, log_decisions=log_decisions
    )
    clusters = merge_clusters_by_campaign_identity(
        clusters, window_hours=window_hours, log_decisions=log_decisions
    )
    clusters = split_indicator_only_from_anchor_clusters(clusters, log_decisions=log_decisions)
    selected = ensure_attack_cluster(clusters, all_alerts, log_decisions=log_decisions)

    if log_decisions:
        log_clusters("prepare_final_selected", selected, window_hours=window_hours)
    return selected


def _cluster_score(cluster: dict[str, Any]) -> float:
    alerts = cluster.get("alerts") or []
    if not alerts:
        return 0.0

    max_risk = max(int(a.get("risk_score") or 0) for a in alerts)
    open_count = sum(1 for a in alerts if str(a.get("status") or "").lower() != "closed")
    shared_entities: set[str] = set()
    for alert in alerts:
        shared_entities.update(str(e) for e in (alert.get("entity_identifiers") or []) if e)

    score = float(max_risk)
    score += len(alerts) * 8.0
    score += open_count * 5.0
    score += min(len(shared_entities), 6) * 3.0

    newest = max(
        (_alert_timestamp(a) for a in alerts if _alert_timestamp(a) is not None),
        default=None,
    )
    if newest is not None:
        age_hours = (datetime.now(timezone.utc) - newest).total_seconds() / 3600.0
        score += max(0.0, 48.0 - age_hours) * 0.5

    return score


def _cluster_is_attack_meaningful(cluster: dict[str, Any]) -> bool:
    alerts = cluster.get("alerts") or []
    if len(alerts) >= 2:
        entity_sets = [set(a.get("entity_identifiers") or []) for a in alerts]
        shared = set.intersection(*entity_sets) if entity_sets else set()
        if shared:
            return True
        if _cluster_campaign_entities(cluster):
            return True
        return max(int(a.get("risk_score") or 0) for a in alerts) >= 70

    if len(alerts) == 1:
        return is_attack_indicative(alerts[0]) and int(alerts[0].get("risk_score") or 0) >= 55

    return False


def select_attack_clusters(
    clusters: list[dict[str, Any]],
    *,
    max_findings: int = 2,
    log_decisions: bool = True,
) -> list[dict[str, Any]]:
    """Keep only high-value attack clusters; cap how many findings we emit."""
    scored: list[tuple[float, dict[str, Any]]] = []
    for idx, cluster in enumerate(clusters):
        meaningful, reason = explain_cluster_meaningful(cluster)
        score_detail = explain_cluster_score(cluster)
        if log_decisions:
            log_step(
                "select_score",
                cluster_index=idx,
                meaningful=meaningful,
                meaningful_reason=reason,
                score=round(score_detail["score"], 2),
                score_parts=score_detail["parts"],
                **format_cluster(cluster, idx),
            )
        if not meaningful:
            continue
        scored.append((score_detail["score"], cluster))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [cluster for _, cluster in scored[:max_findings]]
    if log_decisions:
        log_step(
            "select_summary",
            candidate_clusters=len(clusters),
            meaningful_count=len(scored),
            max_findings=max_findings,
            selected_count=len(selected),
            ranked_scores=[round(s, 2) for s, _ in scored],
        )
    return selected


def ensure_attack_cluster(
    clusters: list[dict[str, Any]],
    all_alerts: list[dict[str, Any]],
    *,
    log_decisions: bool = True,
) -> list[dict[str, Any]]:
    """Guarantee at least one cluster for Attack Discovery output."""
    selected = select_attack_clusters(clusters, log_decisions=log_decisions)
    if selected:
        return selected

    if log_decisions:
        log_step("ensure_fallback", reason="no_meaningful_cluster_pick_highest_risk")

    attack_alerts = filter_attack_alerts(all_alerts, log_decisions=False)
    pool = attack_alerts or all_alerts
    if not pool:
        return []

    best = max(pool, key=lambda a: int(a.get("risk_score") or 0))
    if log_decisions:
        log_step("ensure_fallback_alert", alert_row_id=best.get("alert_row_id"), line=format_alert_line(best))
    return [{"alerts": [best]}]


def average_alert_risk(alerts: list[dict[str, Any]]) -> int:
    """Correlation finding risk = mean of contributing alert risk_score values."""
    scores = [int(a.get("risk_score") or 0) for a in alerts]
    if not scores:
        return 55
    return int(round(sum(scores) / len(scores)))


def derive_title_fallback(cluster: dict[str, Any]) -> str:
    alerts = cluster.get("alerts") or []
    if not alerts:
        return "Attack Discovery — Correlated Activity"

    names = [str(a.get("name") or "").strip() for a in alerts if a.get("name")]
    max_risk = max(int(a.get("risk_score") or 0) for a in alerts)
    joined = " ".join(names).lower()

    if "phish" in joined:
        pattern = "Phishing-to-Compromise"
    elif "lateral" in joined or "psexec" in joined or "rdp" in joined:
        pattern = "Lateral Movement"
    elif "c2" in joined or "beacon" in joined or "outbound" in joined:
        pattern = "Command-and-Control"
    elif "powershell" in joined or "download" in joined:
        pattern = "Execution Chain"
    elif "login" in joined:
        pattern = "Credential Abuse"
    else:
        pattern = "Multi-Stage Attack"

    anchor_label = primary_anchor_display(cluster)
    suffix = f" on {anchor_label}" if anchor_label else ""
    return f"{pattern}{suffix} (risk {max_risk})"
