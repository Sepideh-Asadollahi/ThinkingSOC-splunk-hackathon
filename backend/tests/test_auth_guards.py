from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from config import Settings, get_settings
from main import app


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/api/v1/classification/alert", {}),
        ("post", "/api/v1/analysis/route", {}),
        ("post", "/api/v1/agents/triage", {}),
        ("get", "/api/v1/soc/chat/conversations", None),
        ("get", "/api/v1/soc/chat/conversations/demo-id", None),
        ("delete", "/api/v1/soc/chat/conversations/demo-id", None),
        ("get", "/api/v1/integrations/settings", None),
    ],
)
def test_auth_guard_requires_bearer_token(
    client_with_token: TestClient,
    method: str,
    path: str,
    payload: dict | None,
) -> None:
    request_fn = getattr(client_with_token, method)
    kwargs = {"json": payload} if payload is not None else {}
    response = request_fn(path, **kwargs)
    assert response.status_code == 401


def test_auth_guard_rejects_wrong_bearer_token(client_with_token: TestClient) -> None:
    response = client_with_token.get(
        "/api/v1/integrations/settings",
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/api/v1/classification/alert", {}),
        ("post", "/api/v1/analysis/route", {}),
        ("post", "/api/v1/agents/triage", {}),
    ],
)
def test_sensitive_routes_accept_valid_bearer_guard(
    client_with_token: TestClient,
    method: str,
    path: str,
    payload: dict,
) -> None:
    request_fn = getattr(client_with_token, method)
    response = request_fn(path, json=payload, headers={"Authorization": "Bearer expected-ingest-secret"})
    assert response.status_code not in (401, 403)


def test_integrations_uses_admin_token_when_configured() -> None:
    settings = Settings(
        splunk_mgmt_url="https://127.0.0.1:8089",
        splunk_username="testuser",
        splunk_password="testpass",
        splunk_verify_ssl=False,
        tsoc_postgres_dsn=None,
        tsoc_ingest_token="ingest-token",
        tsoc_admin_token="admin-token",
    )

    def _override() -> Settings:
        return settings

    app.dependency_overrides[get_settings] = _override
    try:
        with TestClient(app) as client:
            ingest_resp = client.get(
                "/api/v1/integrations/settings",
                headers={"Authorization": "Bearer ingest-token"},
            )
            admin_resp = client.get(
                "/api/v1/integrations/settings",
                headers={"Authorization": "Bearer admin-token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert ingest_resp.status_code == 403
    assert admin_resp.status_code not in (401, 403)


def test_rate_limit_enforced_on_sensitive_route() -> None:
    settings = Settings(
        splunk_mgmt_url="https://127.0.0.1:8089",
        splunk_username="testuser",
        splunk_password="testpass",
        splunk_verify_ssl=False,
        tsoc_postgres_dsn=None,
        tsoc_admin_token="admin-token",
        tsoc_rate_limit_enabled=True,
        tsoc_rate_limit_window_seconds=60,
        tsoc_rate_limit_max_requests=2,
    )

    def _override() -> Settings:
        return settings

    app.dependency_overrides[get_settings] = _override
    try:
        with TestClient(app) as client:
            h = {"Authorization": "Bearer admin-token"}
            r1 = client.get("/api/v1/integrations/settings", headers=h)
            r2 = client.get("/api/v1/integrations/settings", headers=h)
            r3 = client.get("/api/v1/integrations/settings", headers=h)
    finally:
        app.dependency_overrides.clear()

    assert r1.status_code != 429
    assert r2.status_code != 429
    assert r3.status_code == 429
