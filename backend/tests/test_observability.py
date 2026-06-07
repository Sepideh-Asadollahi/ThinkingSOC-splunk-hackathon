from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings, get_settings
from main import app

_USERS = [{"user_id": "jdoe", "risk_score": "3", "department": "IT"}]
_ASSETS = [
    {
        "asset_id": "srv-web-01",
        "hostname": "web-prod-01",
        "ip": "10.0.0.5",
        "criticality": "high",
        "risk_score": "4",
    }
]
_RULES = [
    {
        "rule_id": "r-host",
        "priority": "10",
        "enabled": "1",
        "entity_type": "asset",
        "alert_field": "host",
        "inventory_lookup": "tsoc_assets",
        "inventory_field": "hostname",
        "match_type": "exact",
        "on_multiple_matches": "highest_criticality",
    },
    {
        "rule_id": "r-user",
        "priority": "20",
        "enabled": "1",
        "entity_type": "user",
        "alert_field": "user",
        "inventory_lookup": "tsoc_users",
        "inventory_field": "user_id",
        "match_type": "exact",
        "on_multiple_matches": "first",
    },
]


def _classifier_llm_response(track: str, pipeline: str) -> dict:
    return {
        "content": json.dumps(
            {
                "track": track,
                "recommended_pipeline": pipeline,
                "confidence": 0.9,
                "reason": "test classification",
                "signals": ["test"],
                "needs_human_routing": False,
            }
        )
    }


async def _mock_classifier_litellm(settings, messages, **kwargs):
    user = messages[-1]["content"].lower()
    if "cpu" in user and "latency" in user:
        return _classifier_llm_response("observability", "observability")
    if "failed login" in user or "suspicious auth" in user:
        return _classifier_llm_response("security", "security")
    return _classifier_llm_response("unknown", "manual_review")


@pytest.fixture
def client_analysis_router(test_settings: Settings):
    def _override() -> Settings:
        return test_settings.model_copy(
            update={
                "tsoc_classifier_llm": True,
                "litellm_model": "test-model",
                "litellm_api_key": "sk-test",
            }
        )

    with patch(
        "services.alert.alert_classifier_llm.litellm_chat_completion",
        new_callable=AsyncMock,
        side_effect=_mock_classifier_litellm,
    ):
        app.dependency_overrides[get_settings] = _override
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


def test_observability_run_api_offline(client_analysis_router: TestClient) -> None:
    r = client_analysis_router.post(
        "/api/v1/observability/run",
        json={
            "normalized": {"host": "web-prod-01", "service": "payment-api", "cpu": 97.4, "latency_ms": 2200},
            "search_name": "High CPU and latency",
            "users": _USERS,
            "assets": _ASSETS,
            "relationships": _RULES,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["track"] == "observability"
    assert data["entity_resolution"]["resolved_asset_id"] == "srv-web-01"
    assert data["ops_judge"]["verdict"]
    assert data["diagnoser"]["followup_searches"]


def test_analysis_route_observability(client_analysis_router: TestClient) -> None:
    r = client_analysis_router.post(
        "/api/v1/analysis/route",
        json={
            "normalized": {"host": "web-prod-01", "service": "payment-api", "cpu": 95, "latency_ms": 1800},
            "search_name": "Host CPU spike with latency",
            "users": _USERS,
            "assets": _ASSETS,
            "relationships": _RULES,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["track"] == "observability"
    assert data["observability_result"] is not None
    assert data["security_result"] is None


def test_analysis_route_security(client_analysis_router: TestClient) -> None:
    r = client_analysis_router.post(
        "/api/v1/analysis/route",
        json={
            "normalized": {"host": "web-prod-01", "user": "jdoe", "src": "1.2.3.4", "dest": "10.0.0.10"},
            "search_name": "Suspicious auth failed login alert",
            "users": _USERS,
            "assets": _ASSETS,
            "relationships": _RULES,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["track"] == "security"
    assert data["security_result"] is not None


def test_classification_alert_endpoint_with_sid_enrichment(client_analysis_router: TestClient) -> None:
    async def _enrich(*args, **kwargs):
        return {
            "splunk_results": [{"host": "web-prod-01", "cpu": 97.4, "latency_ms": 2000, "service": "payment-api"}],
        }

    with patch("api.routes.analysis.enrich_alert_from_splunk", new_callable=AsyncMock) as m:
        m.side_effect = _enrich
        r = client_analysis_router.post(
            "/api/v1/classification/alert",
            json={"sid": "sid-obs-1", "search_name": "High cpu latency", "normalized": {}},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["track"] == "observability"
    assert data["recommended_pipeline"] == "observability"


def test_observability_run_by_sid_api_offline(client_analysis_router: TestClient) -> None:
    async def _enrich(*args, **kwargs):
        return {
            "splunk_results": [
                {"host": "web-prod-01", "service": "payment-api", "cpu": 95},
                {"host": "web-prod-01", "service": "payment-api", "latency_ms": 1500},
            ],
        }

    with patch("services.observability_analysis.observability_analysis_batch.enrich_alert_from_splunk", new_callable=AsyncMock) as m:
        m.side_effect = _enrich
        r = client_analysis_router.post(
            "/api/v1/observability/run-by-sid",
            json={
                "sid": "sid-obs-batch-1",
                "search_name": "obs batch",
                "users": _USERS,
                "assets": _ASSETS,
                "relationships": _RULES,
            },
        )
    assert r.status_code == 200
    data = r.json()
    assert data["sid"] == "sid-obs-batch-1"
    assert data["analyzed_row_count"] == 2
    assert data["rows"][0]["ok"] is True
    assert data["rows"][0]["result"]["track"] == "observability"


def test_observability_prompts_follow_json_strict_style() -> None:
    from services.observability_analysis.observability_prompts import (
        load_observability_diagnoser_system_prompt,
        load_observability_ops_judge_system_prompt,
        load_observability_responder_system_prompt,
    )

    for loader in (
        load_observability_diagnoser_system_prompt,
        load_observability_responder_system_prompt,
        load_observability_ops_judge_system_prompt,
    ):
        text = loader()
        assert "Your ENTIRE response MUST be a single, valid JSON object" in text
        assert "no markdown code fence" in text
        assert "{{" in text and "}}" in text
