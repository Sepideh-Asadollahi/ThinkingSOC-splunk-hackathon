"""Inventory enrich HTTP route (offline mode; no Splunk)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_enrich_relationship_links_user_when_only_asset_in_alert(client: TestClient) -> None:
    body = {
        "normalized": {"host": "host-a"},
        "users": [{"user_id": "u2", "risk_score": "5", "department": "Finance"}],
        "assets": [
            {"asset_id": "a1", "hostname": "host-a", "ip": "10.0.0.1", "criticality": "high", "risk_score": "8"},
        ],
        "relationships": [
            {"relationship_id": "rel-u2-a1", "user_id": "u2", "asset_id": "a1"},
        ],
    }
    r = client.post("/api/v1/inventory/enrich", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["resolved_user_id"] == "u2"
    assert data["resolved_asset_id"] == "a1"
    assert "rel-u2-a1" in data["matched_relationship_ids"]
    assert "relationship" in data["notes"].lower()


def test_enrich_offline(client: TestClient) -> None:
    body = {
        "normalized": {"host": "host-a", "user": "u2"},
        "users": [{"user_id": "u2", "risk_score": "2"}],
        "assets": [
            {"asset_id": "a1", "hostname": "host-a", "ip": "10.0.0.1", "criticality": "high"},
        ],
        "relationships": [],
    }
    r = client.post("/api/v1/inventory/enrich", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["resolved_asset_id"] == "a1"
    assert data["resolved_user_id"] == "u2"


def test_enrich_partial_override_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/v1/inventory/enrich",
        json={"normalized": {}, "users": [], "assets": None, "relationships": None},
    )
    assert r.status_code == 400


def test_inventory_status(client: TestClient) -> None:
    r = client.get("/api/v1/inventory/status")
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "postgresql"
