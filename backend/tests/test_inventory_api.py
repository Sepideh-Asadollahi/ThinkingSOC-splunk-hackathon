"""Inventory CRUD API tests (mocked PostgreSQL layer)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings, get_settings
from main import app
from models.inventory import RelationshipRecord, UserRecord


@pytest.fixture
def pg_client() -> TestClient:
    def _override() -> Settings:
        return Settings(tsoc_postgres_dsn="postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc")

    app.dependency_overrides[get_settings] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_inventory_users_list_requires_pg_mock(pg_client: TestClient) -> None:
    with patch("api.routes.inventory.splunk_store_configured", return_value=True):
        with patch("api.routes.inventory.list_users", new_callable=AsyncMock) as m:
            m.return_value = [
                UserRecord(user_id="u1", risk_score=1),
            ]
            r = pg_client.get("/api/v1/inventory/users")
    assert r.status_code == 200
    assert r.json()[0]["user_id"] == "u1"


def test_inventory_users_503_without_dsn(client: TestClient) -> None:
    r = client.get("/api/v1/inventory/users")
    assert r.status_code == 503


def test_inventory_relationships_list(pg_client: TestClient) -> None:
    with patch("api.routes.inventory.splunk_store_configured", return_value=True):
        with patch("api.routes.inventory.list_relationships", new_callable=AsyncMock) as m:
            m.return_value = [
                RelationshipRecord(
                    relationship_id="rel-1",
                    user_id="u1",
                    asset_id="a1",
                )
            ]
            r = pg_client.get("/api/v1/inventory/relationships")
    assert r.status_code == 200
    assert r.json()[0]["relationship_id"] == "rel-1"
