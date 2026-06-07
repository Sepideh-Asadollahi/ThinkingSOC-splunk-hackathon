from __future__ import annotations

import pytest

from graph_pipelines.attack_alert_filter import apply_indicator_split_merge_guard
from graph_pipelines.llm_stub import (
    _heuristic_cluster_merge,
    merge_cluster_alerts,
    partition_clusters_by_merge,
)


def _alert(aid: str, entities: list[str], *, timestamp: str = "2026-05-20T10:00:00Z") -> dict:
    return {
        "alert_row_id": aid,
        "name": "test",
        "risk_score": 70,
        "entity_identifiers": entities,
        "timestamp": timestamp,
    }


def test_partition_single_clusters():
    merge_result = {"merge_groups": []}
    assert partition_clusters_by_merge(2, merge_result) == [[0], [1]]


def test_partition_merged_pair():
    merge_result = {"merge_groups": [[0, 1]]}
    assert partition_clusters_by_merge(2, merge_result) == [[0, 1]]


def test_partition_transitive_merge():
    merge_result = {"merge_groups": [[0, 1], [1, 2]]}
    assert partition_clusters_by_merge(3, merge_result) == [[0, 1, 2]]


def test_merge_cluster_alerts_dedupes():
    clusters = [
        {"alerts": [_alert("a1", ["hostname:H1"])]},
        {"alerts": [_alert("a1", ["hostname:H1"]), _alert("a2", ["hostname:H2"])]},
    ]
    merged = merge_cluster_alerts(clusters, [0, 1])
    ids = [a["alert_row_id"] for a in merged["alerts"]]
    assert ids == ["a1", "a2"]


def test_merge_cluster_alerts_sorts_chronologically():
    clusters = [
        {
            "alerts": [
                _alert("ALERT-090", ["username:jdoe"], timestamp="2026-05-25T06:13:51Z"),
                _alert("ALERT-099", ["hostname:SERVER01"], timestamp="2026-05-28T06:13:52Z"),
                _alert("ALERT-101", ["hostname:SERVER01"], timestamp="2026-05-29T06:13:52Z"),
                _alert("ALERT-102", ["hostname:SERVER01"], timestamp="2026-05-29T10:13:52Z"),
            ]
        },
        {
            "alerts": [
                _alert("ALERT-091", ["ipv4:203.0.113.50"], timestamp="2026-05-25T06:38:51Z"),
            ]
        },
    ]
    merged = merge_cluster_alerts(clusters, [0, 1])
    ids = [a["alert_row_id"] for a in merged["alerts"]]
    assert ids == ["ALERT-090", "ALERT-091", "ALERT-099", "ALERT-101", "ALERT-102"]


def test_heuristic_merges_on_shared_entity():
    clusters = [
        {"alerts": [_alert("a1", ["username:jdoe", "hostname:SERVER01"])]},
        {"alerts": [_alert("a2", ["username:jdoe", "hostname:OTHER"])]},
    ]
    result = _heuristic_cluster_merge(clusters)
    assert result["merge_groups"] == [[0, 1]]
    assert "overlapping" in result["reasoning"].lower() or "shared" in result["reasoning"].lower()


def test_ioc_split_guard_blocks_llm_remerge():
    clusters = [
        {
            "alerts": [
                _alert("ALERT-090", ["username:jdoe", "ipv4:203.0.113.50"], timestamp="2026-05-25T06:13:51Z"),
                _alert("ALERT-102", ["hostname:SERVER01"], timestamp="2026-05-29T10:13:52Z"),
            ]
        },
        {"alerts": [_alert("ALERT-091", ["ipv4:203.0.113.50"], timestamp="2026-05-25T06:38:51Z")]},
    ]
    llm_merge = {"merge_groups": [[0, 1]], "potential_links": [], "reasoning": "test", "source": "llm"}
    guarded = apply_indicator_split_merge_guard(clusters, llm_merge)
    assert guarded["merge_groups"] == []
    assert partition_clusters_by_merge(2, guarded) == [[0], [1]]


def test_heuristic_keeps_separate_without_overlap():
    clusters = [
        {"alerts": [_alert("a1", ["hostname:HOST_A"])]},
        {"alerts": [_alert("a2", ["hostname:HOST_B"])]},
    ]
    result = _heuristic_cluster_merge(clusters)
    assert result["merge_groups"] == []
    assert partition_clusters_by_merge(2, result) == [[0], [1]]


@pytest.mark.asyncio
async def test_correlate_single_cluster():
    from graph_pipelines.llm_stub import correlate_clusters

    cluster = {"alerts": [_alert("a1", ["hostname:H1"])]}
    result = await correlate_clusters([cluster])
    assert result["merge_groups"] == []
    assert "single" in result["reasoning"].lower()
