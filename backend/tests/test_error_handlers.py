from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from api.app_errors import AppError


def test_structured_error_body_on_app_error(client: TestClient) -> None:
    async def _fail(*_args, **_kwargs):
        raise AppError.bad_request("sid missing", code="missing_sid", reason="Webhook must include sid or result.")

    with patch("api.routes.ingest.enrich_alert_from_splunk", new_callable=AsyncMock) as m:
        m.side_effect = _fail
        r = client.post("/api/v1/alerts/splunk-ingest", json={"search_name": "x"})

    assert r.status_code == 400
    data = r.json()
    assert data["detail"] == "sid missing"
    assert data["error"]["code"] == "missing_sid"
    assert "reason" in data["error"]
    assert data["request_id"]


def test_splunk_job_not_found_has_clear_reason(client: TestClient) -> None:
    request = httpx.Request("GET", "https://127.0.0.1:8089/services/search/jobs/demo")
    response = httpx.Response(404, request=request, text="Not Found")
    err = httpx.HTTPStatusError("404", request=request, response=response)

    async def _fail(*_args, **_kwargs):
        raise err

    with patch("api.routes.ingest.enrich_alert_from_splunk", new_callable=AsyncMock) as m:
        m.side_effect = _fail
        r = client.post("/api/v1/alerts/splunk-ingest", json={"sid": "demo", "search_name": "s"})

    assert r.status_code == 502
    data = r.json()
    assert data["error"]["code"] == "splunk_job_not_found"
    assert "sid=" in data["error"]["reason"]


def test_unhandled_exception_returns_safe_message(client: TestClient) -> None:
    async def _boom(*_args, **_kwargs):
        raise RuntimeError("connection refused")

    with patch("api.routes.ingest.enrich_alert_from_splunk", new_callable=AsyncMock) as m:
        m.side_effect = _boom
        r = client.post("/api/v1/alerts/splunk-ingest", json={"sid": "1", "search_name": "s"})

    assert r.status_code == 500
    data = r.json()
    assert data["error"]["code"] == "internal_error"
    assert data["detail"] == "An unexpected error occurred"
    assert "RuntimeError" in data["error"]["reason"]
