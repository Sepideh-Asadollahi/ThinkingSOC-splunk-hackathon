from __future__ import annotations

from graph_core.entity_taxonomy import EntityKind, entity_kind, is_indicator_only_alert
from graph_pipelines.attack_alert_filter import (
    apply_indicator_split_merge_guard,
    merge_blocked_by_indicator_split,
    split_indicator_only_from_anchor_clusters,
)


def _alert(aid: str, entities: list[str]) -> dict:
    return {"alert_row_id": aid, "name": "test", "risk_score": 70, "entity_identifiers": entities}


def test_entity_kind_classifies_by_prefix_not_demo_ids():
    assert entity_kind("username:any@org") == EntityKind.ANCHOR
    assert entity_kind("host:ws-42") == EntityKind.ANCHOR
    assert entity_kind("ipv4:198.51.100.1") == EntityKind.INDICATOR
    assert entity_kind("sha256:deadbeef") == EntityKind.INDICATOR
    assert entity_kind("customlabel:foo") == EntityKind.OTHER


def test_split_indicator_only_uses_taxonomy():
    clusters = [
        {
            "alerts": [
                _alert("A1", ["username:u1", "hostname:h1"]),
                _alert("A2", ["ipv4:198.51.100.1"]),
            ]
        }
    ]
    out = split_indicator_only_from_anchor_clusters(clusters, log_decisions=False)
    assert len(out) == 2
    assert {a["alert_row_id"] for c in out for a in c["alerts"]} == {"A1", "A2"}


def test_indicator_merge_guard_blocks_ip_only_singleton():
    clusters = [
        {"alerts": [_alert("K1", ["username:u1", "hostname:h1"])]},
        {"alerts": [_alert("K2", ["ipv4:203.0.113.1"])]},
    ]
    assert merge_blocked_by_indicator_split(clusters[0], clusters[1])
    guarded = apply_indicator_split_merge_guard(clusters, {"merge_groups": [[0, 1]], "potential_links": []})
    assert guarded["merge_groups"] == []
