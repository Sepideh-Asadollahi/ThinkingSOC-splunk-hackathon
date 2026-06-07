from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


def test_splunk_ingest_success(client: TestClient, mock_enrich_ok: AsyncMock) -> None:
    r = client.post(
        "/api/v1/alerts/splunk-ingest",
        json={
            "sid": "scheduler__nobody__search_abc123",
            "search_name": "test_alert",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["sid"] == "scheduler__nobody__search_abc123"
    assert data["search_name"] == "test_alert"
    assert data["splunk_results_row_count"] == 2
    mock_enrich_ok.assert_awaited_once()


def test_splunk_ingest_missing_sid_returns_400(
    client: TestClient,
    mock_enrich_value_error: AsyncMock,
) -> None:
    r = client.post(
        "/api/v1/alerts/splunk-ingest",
        json={"search_name": "x"},
    )
    assert r.status_code == 400
    assert "sid" in r.json()["detail"].lower()


def test_splunk_ingest_splunk_error_returns_502(
    client: TestClient,
    mock_enrich_generic_error: AsyncMock,
) -> None:
    r = client.post(
        "/api/v1/alerts/splunk-ingest",
        json={"sid": "123", "search_name": "s"},
    )
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"


def test_splunk_ingest_requires_bearer_when_token_configured(
    client_with_token: TestClient,
    mock_enrich_ok: AsyncMock,
) -> None:
    r = client_with_token.post(
        "/api/v1/alerts/splunk-ingest",
        json={"sid": "1", "search_name": "s"},
    )
    assert r.status_code == 401


def test_splunk_ingest_rejects_wrong_bearer(
    client_with_token: TestClient,
    mock_enrich_ok: AsyncMock,
) -> None:
    r = client_with_token.post(
        "/api/v1/alerts/splunk-ingest",
        json={"sid": "1", "search_name": "s"},
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 403


def test_splunk_ingest_accepts_valid_bearer(
    client_with_token: TestClient,
    mock_enrich_ok: AsyncMock,
) -> None:
    r = client_with_token.post(
        "/api/v1/alerts/splunk-ingest",
        json={"sid": "1", "search_name": "s"},
        headers={"Authorization": "Bearer expected-ingest-secret"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_splunk_ingest_debug_returns_payload(
    client: TestClient,
    mock_enrich_ok: AsyncMock,
) -> None:
    r = client.post(
        "/api/v1/alerts/splunk-ingest-debug",
        json={"sid": "1", "search_name": "s"},
    )
    assert r.status_code == 200
    assert r.json()["splunk_results_row_count"] == 2


def test_splunk_ingest_accepts_webhook_payload_shape(
    client: TestClient,
    mock_enrich_ok: AsyncMock,
) -> None:
    r = client.post(
        "/api/v1/alerts/splunk-ingest",
        json={
            "sid": "scheduler_admin_search_W2_at_14232356_132",
            "search_name": "webhook_alert",
            "owner": "admin",
            "app": "search",
            "result": {"host": "web-01", "severity": "high", "count": "8"},
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["sid"] == "scheduler_admin_search_W2_at_14232356_132"
    assert data["search_name"] == "webhook_alert"
    mock_enrich_ok.assert_awaited_once()
