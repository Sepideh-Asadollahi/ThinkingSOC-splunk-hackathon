from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from config import Settings, get_settings
from main import app
from models.agentic_ops import AlertClassificationResult

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


@pytest.fixture
def client_agentic(test_settings: Settings):
    def _override() -> Settings:
        return test_settings

    app.dependency_overrides[get_settings] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_assistant_spl_suggest_rule_based(client_agentic: TestClient) -> None:
    r = client_agentic.post(
        "/api/v1/assistant/spl-suggest",
        json={
            "normalized": {"host": "web-prod-01", "user": "jdoe", "src": "1.2.3.4"},
            "search_name": "Suspicious auth activity",
            "objective": "collect root cause timeline",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "rule_based"
    assert data["root_cause_spl"]["spl"].lower().startswith("search")


def test_agents_triage_security_flow(client_agentic: TestClient) -> None:
    classification = AlertClassificationResult(
        track="security",
        recommended_pipeline="security",
        confidence=0.9,
        reason="test classification",
        signals=["auth"],
        needs_human_routing=False,
    )
    with patch(
        "services.alert.agent_triage.classify_with_optional_mcp",
        new_callable=AsyncMock,
        return_value=(classification, None, False),
    ):
        r = client_agentic.post(
            "/api/v1/agents/triage",
            json={
                "normalized": {"host": "web-prod-01", "user": "jdoe", "src": "1.2.3.4", "dest": "10.0.0.10"},
                "search_name": "Suspicious failed login",
                "users": _USERS,
                "assets": _ASSETS,
                "relationships": _RULES,
                "operator_goal": "confirm lateral movement",
            },
        )
    assert r.status_code == 200
    data = r.json()
    assert data["classification"]["recommended_pipeline"] in ("security", "observability", "manual_review")
    assert data["security_result"] is not None
    assert data["suggested_spl"] is not None
    assert len(data["next_actions"]) >= 2

