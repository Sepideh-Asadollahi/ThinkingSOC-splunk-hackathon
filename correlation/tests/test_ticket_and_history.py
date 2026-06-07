from __future__ import annotations

import pytest

FINDING_ID = "7fda487b-c5fe-4b88-b153-0958d74e4aec"


@pytest.mark.asyncio
async def test_patch_ticket_note(client):
    resp = await client.patch(
        f"/api/v1/graph/findings/{FINDING_ID}/ticket",
        json={
            "ticket_status": "in_progress",
            "new_note": "Investigating RDP session",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticket_status"] == "in_progress"
    notes = data["details"].get("ticket_notes") or []
    assert any("Investigating RDP session" in n.get("text", "") for n in notes)


@pytest.mark.asyncio
async def test_discover_finding_includes_historical_incident(client):
    resp = await client.post(
        "/api/v1/graph/analysis/discover-attack-paths",
        json={
            "analysis_types": ["smart"],
            "limit_to_latest_alerts": 50,
            "force_reanalysis": True,
        },
    )
    assert resp.status_code == 202
    operation_id = resp.json()["operation_id"]

    import asyncio

    finding_ids: list[str] = []
    for _ in range(30):
        poll = await client.get(
            f"/api/v1/graph/analysis/operations/{operation_id}/status"
        )
        body = poll.json()
        if body["status"] == "completed":
            finding_ids = body.get("result_payload", {}).get("finding_ids") or []
            break
        if body["status"] == "failed":
            pytest.fail(body.get("message", body))
        await asyncio.sleep(0.3)

    assert finding_ids
    detail = await client.get(f"/api/v1/graph/findings/{finding_ids[0]}")
    assert detail.status_code == 200
    historical = detail.json()["details"].get("historical_related_incidents") or []
    incident_ids = {h.get("incident_id") for h in historical}
    assert "INC-OLD-001" in incident_ids
