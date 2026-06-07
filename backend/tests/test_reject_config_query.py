"""URL query params must not override server configuration."""

from __future__ import annotations

from fastapi.testclient import TestClient

from middleware.reject_config_query import forbidden_config_query_keys


def test_forbidden_config_query_keys_detects_legacy_and_env_style() -> None:
    keys = forbidden_config_query_keys(
        {
            "auto_analyze": "true",
            "async_mode": "true",
            "TSOC_INGEST_AUTO_ANALYZE": "false",
            "splunk_verify_ssl": "0",
            "sid": "abc",
            "limit": "10",
        }
    )
    assert keys == [
        "TSOC_INGEST_AUTO_ANALYZE",
        "async_mode",
        "auto_analyze",
        "splunk_verify_ssl",
    ]


def test_ingest_rejects_auto_analyze_query(client: TestClient) -> None:
    r = client.post(
        "/api/v1/alerts/splunk-ingest?auto_analyze=true&async_mode=true",
        json={"sid": "scheduler_123", "search_name": "demo", "result": {"host": "h1"}},
    )
    assert r.status_code == 400
    body = r.json()
    assert "forbidden_query_params" in body
    assert "auto_analyze" in body["forbidden_query_params"]


def test_storage_allows_data_filters(client: TestClient) -> None:
    r = client.get("/api/v1/storage/events?sid=test&record_type=soc_analysis&limit=5")
    assert r.status_code != 400 or "forbidden_query_params" not in r.json()
