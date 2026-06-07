from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_discover_attack_paths_completes(client):
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
    assert operation_id

    status = "running"
    payload = None
    body: dict = {}
    for _ in range(30):
        poll = await client.get(
            f"/api/v1/graph/analysis/operations/{operation_id}/status"
        )
        assert poll.status_code == 200
        body = poll.json()
        status = body["status"]
        if status in ("completed", "failed"):
            payload = body.get("result_payload")
            break
        await asyncio.sleep(0.3)

    assert status == "completed", body.get("message", body)
    assert payload is not None
    assert payload.get("findings_created", 0) >= 1
    assert payload.get("finding_ids")

    detail_id = payload["finding_ids"][0]
    detail = await client.get(f"/api/v1/graph/findings/{detail_id}")
    assert detail.status_code == 200
    historical = detail.json()["details"].get("historical_related_incidents") or []
    assert any(h.get("incident_id") == "INC-OLD-001" for h in historical)

    list_resp = await client.get(
        "/api/v1/graph/findings",
        params={"limit": 50, "offset": 0, "finding_type": "smart_attack_discovery"},
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) >= 1
