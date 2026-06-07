"""Investigation timeline and analyst-actions HTTP API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings, get_settings
from main import app

AUTH = {"Authorization": "Bearer expected-ingest-secret"}


@pytest.fixture
def client_investigation(test_settings_with_ingest_token: Settings):
    def _override() -> Settings:
        return test_settings_with_ingest_token.model_copy(
            update={"tsoc_postgres_dsn": "postgresql://test"}
        )

    app.dependency_overrides[get_settings] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_timeline_503_without_postgres(client_with_token: TestClient) -> None:
    r = client_with_token.get(
        "/api/v1/investigation/records/1/timeline",
        headers=AUTH,
    )
    assert r.status_code == 503


def test_timeline_404_when_record_missing(client_investigation: TestClient) -> None:
    with patch(
        "api.routes.investigation.build_investigation_timeline",
        new_callable=AsyncMock,
        return_value={"record_id": 99, "found": False, "steps": []},
    ):
        r = client_investigation.get(
            "/api/v1/investigation/records/99/timeline",
            headers=AUTH,
        )
    assert r.status_code == 404


def test_timeline_ok(client_investigation: TestClient) -> None:
    payload = {
        "record_id": 10,
        "found": True,
        "sid": "sid-1",
        "search_name": "Brute Force",
        "steps": [
            {
                "record_id": 1,
                "record_type": "splunk_ingest",
                "title": "Splunk ingest",
                "description": "Alert received",
                "detail": None,
                "created_at": "2026-05-20T10:00:00+00:00",
                "is_current_record": False,
                "is_analyst_action": False,
            },
            {
                "record_id": 10,
                "record_type": "soc_analysis",
                "title": "SOC analysis",
                "description": "Pipeline completed",
                "detail": "Verdict suspicious",
                "created_at": "2026-05-20T12:00:00+00:00",
                "is_current_record": True,
                "is_analyst_action": False,
            },
        ],
    }
    with patch(
        "api.routes.investigation.build_investigation_timeline",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        r = client_investigation.get(
            "/api/v1/investigation/records/10/timeline",
            headers=AUTH,
        )
    assert r.status_code == 200
    body = r.json()
    assert body["sid"] == "sid-1"
    assert len(body["steps"]) == 2
    assert body["steps"][0]["record_type"] == "splunk_ingest"


def test_analyst_actions_get_empty(client_investigation: TestClient) -> None:
    with patch(
        "api.routes.investigation.list_analyst_actions_for_record",
        new_callable=AsyncMock,
        return_value=[],
    ):
        r = client_investigation.get(
            "/api/v1/investigation/records/5/analyst-actions",
            headers=AUTH,
        )
    assert r.status_code == 200
    assert r.json()["count"] == 0
    assert r.json()["results"] == []


def test_analyst_actions_post_acknowledge(client_investigation: TestClient) -> None:
    saved = {
        "ok": True,
        "postgres_configured": True,
        "event": {"action": "acknowledge"},
        "created_at": "2026-05-22T10:00:00+00:00",
    }
    listed = [
        {
            "id": 100,
            "created_at": "2026-05-22T10:00:00+00:00",
            "action": "acknowledge",
            "note": "Reviewed",
            "recommended_step": "Monitor",
            "investigation_record_id": 5,
        }
    ]
    with (
        patch(
            "api.routes.investigation.record_analyst_action",
            new_callable=AsyncMock,
            return_value=saved,
        ),
        patch(
            "api.routes.investigation.list_analyst_actions_for_record",
            new_callable=AsyncMock,
            return_value=listed,
        ),
    ):
        r = client_investigation.post(
            "/api/v1/investigation/records/5/analyst-actions",
            headers=AUTH,
            json={"action": "acknowledge", "note": "Reviewed"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["latest"]["action"] == "acknowledge"
    assert body["results"][0]["note"] == "Reviewed"


def test_analyst_actions_post_404(client_investigation: TestClient) -> None:
    with patch(
        "api.routes.investigation.record_analyst_action",
        new_callable=AsyncMock,
        side_effect=LookupError("Record not found"),
    ):
        r = client_investigation.post(
            "/api/v1/investigation/records/404/analyst-actions",
            headers=AUTH,
            json={"action": "escalate"},
        )
    assert r.status_code == 404


def test_analyst_actions_post_400_invalid_action(client_investigation: TestClient) -> None:
    r = client_investigation.post(
        "/api/v1/investigation/records/5/analyst-actions",
        headers=AUTH,
        json={"action": "block_ip"},
    )
    assert r.status_code == 422


def test_analyst_actions_post_502_when_persist_fails(client_investigation: TestClient) -> None:
    with patch(
        "api.routes.investigation.record_analyst_action",
        new_callable=AsyncMock,
        return_value={"ok": False, "postgres_configured": True},
    ):
        r = client_investigation.post(
            "/api/v1/investigation/records/5/analyst-actions",
            headers=AUTH,
            json={"action": "escalate"},
        )
    assert r.status_code == 502
