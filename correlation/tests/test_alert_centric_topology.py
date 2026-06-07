from __future__ import annotations

import pytest

from graph_crud.alert_centric import (
    _bridge_text,
    _dedupe_parallel_caused_edges,
    build_alert_centric_tree,
)
from graph_schemas.exploration import GraphEdge, GraphNode

FINDING_ID = "7fda487b-c5fe-4b88-b153-0958d74e4aec"


def test_bridge_text_formats_long_deltas():
    assert _bridge_text(900) == "Sequential Step (+15m)"
    assert _bridge_text(259200) == "Sequential Step (+3d)"


def test_dedupe_parallel_caused_edges_keeps_one_per_pair():
    edges = [
        GraphEdge(
            id="seq_a_b",
            **{"from": "a"},
            to="b",
            label="CAUSED",
            properties={"narrative": "Sequential Step (+15m)", "time_delta_seconds": 900},
        ),
        GraphEdge(
            id="neo4j_rid",
            **{"from": "a"},
            to="b",
            label="CAUSED",
            properties={"confidence": "chronological_sequence", "time_delta_seconds": 900},
        ),
    ]
    out = _dedupe_parallel_caused_edges(edges)
    caused = [e for e in out if e.label == "CAUSED"]
    assert len(caused) == 1
    assert caused[0].properties.get("narrative") == "Sequential Step (+15m)"


def test_build_alert_centric_tree_flat_steps():
    nodes = [
        GraphNode(
            id="n1",
            label="A1",
            group=["Alert"],
            properties={"timestamp": "2026-05-20T10:00:00Z", "risk_score": 75, "name": "RDP"},
        ),
        GraphNode(
            id="n2",
            label="A2",
            group=["Alert"],
            properties={"timestamp": "2026-05-20T10:15:00Z", "risk_score": 78, "name": "PsExec"},
        ),
    ]
    edges = [
        GraphEdge(
            id="e1",
            **{"from": "n1"},
            to="n2",
            label="CAUSED",
            properties={"time_delta_seconds": 900},
        )
    ]
    trees = build_alert_centric_tree(nodes, edges)
    assert len(trees) == 2
    assert trees[0].step == "1"
    assert trees[1].step == "2"
    assert trees[1].edge_context is not None
    assert "15m" in trees[1].edge_context or "900" in trees[1].edge_context


@pytest.mark.asyncio
async def test_alert_topology_caused_chain(client):
    resp = await client.get(f"/api/v1/graph/topology/{FINDING_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["nodes"]) >= 2
    assert data["edges"]
    caused = [e for e in data["edges"] if e["label"] == "CAUSED"]
    assert len(caused) >= 1


@pytest.mark.asyncio
async def test_alert_attack_tree_endpoint(client):
    resp = await client.get(f"/api/v1/graph/attack-tree/{FINDING_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["attack_trees"]) >= 2
    assert data["attack_trees"][0]["type"] == "Alert"
