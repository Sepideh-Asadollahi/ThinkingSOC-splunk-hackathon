from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_correlate_alert_101_finds_099(client):
    resp = await client.post(
        "/api/v1/graph/internal/correlate",
        headers={"X-Demo-Api-Key": "dev-key"},
        json={
            "entity_identifiers": ["hostname:SERVER01", "username:jdoe@corp.local"],
            "current_alert_row_id": "ALERT-101",
            "depth": 2,
            "max_questions": 0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = [a["alert_row_id"] for a in data["correlated_alerts"]]
    assert "ALERT-099" in ids
    match = next(a for a in data["correlated_alerts"] if a["alert_row_id"] == "ALERT-099")
    assert "hostname:SERVER01" in match["entities_in_common"]
    assert data["total_found"] >= 1
