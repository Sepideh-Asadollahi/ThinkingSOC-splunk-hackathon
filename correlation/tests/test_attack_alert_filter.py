from __future__ import annotations

from datetime import datetime, timedelta, timezone

from graph_pipelines.attack_alert_filter import (
    average_alert_risk,
    ensure_attack_cluster,
    enrich_clusters_with_related_alerts,
    filter_attack_alerts,
    group_alerts_by_shared_entity,
    is_attack_indicative,
    prepare_attack_clusters,
    select_attack_clusters,
)


def _alert(
    aid: str,
    name: str,
    risk: int,
    entities: list[str],
    *,
    status: str = "open",
    days_ago: float = 0,
) -> dict:
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "alert_row_id": aid,
        "name": name,
        "risk_score": risk,
        "status": status,
        "entity_identifiers": entities,
        "timestamp": ts,
    }


def test_is_attack_indicative_filters_noise():
    assert is_attack_indicative(_alert("1", "Informational audit log", 30, [])) is False
    assert is_attack_indicative(_alert("2", "Suspicious RDP session", 50, ["hostname:SERVER01"])) is True
    assert is_attack_indicative(_alert("3", "Generic event", 60, [])) is True


def test_group_alerts_by_shared_entity_only_merges_shared_entities():
    alerts = [
        _alert("a1", "Phishing email", 70, ["username:jdoe", "hostname:SERVER01"]),
        _alert("a2", "PsExec lateral movement", 78, ["username:jdoe", "hostname:SERVER01"]),
        _alert("a3", "Unrelated DNS query", 40, ["hostname:OTHER"]),
    ]
    attack_only = filter_attack_alerts(alerts)
    clusters = group_alerts_by_shared_entity(attack_only)
    selected = select_attack_clusters(clusters)

    assert len(attack_only) == 2
    assert len(selected) == 1
    assert len(selected[0]["alerts"]) == 2


def test_ensure_attack_cluster_always_returns_one():
    alerts = [_alert("solo", "Generic event", 35, ["hostname:LOW"])]
    clusters = group_alerts_by_shared_entity(alerts)
    assert select_attack_clusters(clusters) == []

    fallback = ensure_attack_cluster(clusters, alerts)
    assert len(fallback) == 1
    assert fallback[0]["alerts"][0]["alert_row_id"] == "solo"


def test_singleton_risk_55_is_meaningful():
    alerts = [_alert("low", "Suspicious email link", 55, ["username:jdoe"], status="closed", days_ago=5)]
    clusters = group_alerts_by_shared_entity(alerts)
    assert select_attack_clusters(clusters) == [clusters[0]]


def test_demo_campaign_includes_phishing_precursor():
    """Operation Shadow Login: ALERT-090 (5d) should join jdoe/SERVER01 chain within 7d window."""
    alerts = [
        _alert("ALERT-090", "Suspicious email link", 55, ["username:jdoe@corp.local", "ipv4:203.0.113.50"], status="closed", days_ago=5),
        _alert("ALERT-099", "Unusual login", 60, ["username:jdoe@corp.local", "hostname:SERVER01"], days_ago=2),
        _alert("ALERT-101", "Suspicious RDP", 75, ["username:jdoe@corp.local", "hostname:SERVER01"], days_ago=1),
        _alert("ALERT-102", "PsExec lateral movement", 78, ["username:jdoe@corp.local", "hostname:SERVER01"], days_ago=0.8),
        _alert(
            "ALERT-091",
            "Outbound C2 beacon",
            65,
            ["ipv4:203.0.113.50"],
            status="closed",
            days_ago=5,
        ),
    ]
    selected = prepare_attack_clusters(alerts, window_hours=168)
    main = max(selected, key=lambda c: len(c.get("alerts") or []))
    main_ids = {a["alert_row_id"] for a in main["alerts"]}

    assert "ALERT-099" in main_ids
    assert "ALERT-101" in main_ids
    assert "ALERT-102" in main_ids
    assert "ALERT-090" in main_ids
    assert "ALERT-091" not in main_ids


def test_enrich_attaches_related_user_alert():
    cluster = {"alerts": [_alert("a2", "RDP", 75, ["username:jdoe", "hostname:SERVER01"], days_ago=1)]}
    pool = [
        _alert("a1", "Suspicious email link", 55, ["username:jdoe"], status="closed", days_ago=5),
    ]
    enriched = enrich_clusters_with_related_alerts([cluster], pool, window_hours=168)
    ids = {a["alert_row_id"] for a in enriched[0]["alerts"]}
    assert ids == {"a1", "a2"}


def test_average_alert_risk_is_mean_of_contributing_scores():
    alerts = [
        _alert("a1", "Phish", 60, []),
        _alert("a2", "RDP", 80, []),
        _alert("a3", "PsExec", 70, []),
    ]
    assert average_alert_risk(alerts) == 70


def test_average_alert_risk_empty_defaults():
    assert average_alert_risk([]) == 55
