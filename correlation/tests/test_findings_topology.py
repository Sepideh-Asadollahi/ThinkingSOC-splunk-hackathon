from __future__ import annotations

import pytest

FINDING_ID = "7fda487b-c5fe-4b88-b153-0958d74e4aec"


@pytest.mark.asyncio
async def test_findings_list_includes_gf_0007(client):
    resp = await client.get(
        "/api/v1/graph/findings",
        params={"limit": 100, "offset": 0, "finding_type": "smart_attack_discovery"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    gf7 = next((i for i in data["items"] if i.get("display_id") == "GF-0007"), None)
    assert gf7 is not None
    assert gf7["risk_score"] == 67


@pytest.mark.asyncio
async def test_topology_alert_centric_chain(client):
    resp = await client.get(f"/api/v1/graph/topology/{FINDING_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["nodes"]) >= 2
    assert data["edges"]
    caused = [e for e in data["edges"] if e["label"] == "CAUSED"]
    assert len(caused) >= 1
