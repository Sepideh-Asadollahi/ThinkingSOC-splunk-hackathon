"""Agent triage with MCP enrichment (mocked)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings, get_settings
from main import app
from models.agentic_ops import AlertClassificationResult
from models.analysis import HunterSection, JudgeVerdict, RootCauseSpl, SocAnalysisResult
from models.enrichment import EnrichmentResult
from models.mcp import McpAlertContext


def _minimal_soc_result() -> SocAnalysisResult:
    return SocAnalysisResult(
        defender="ok",
        hunter=HunterSection(narrative="hunt", splunk_search_suggestions=["index=main"]),
        judge=JudgeVerdict(
            verdict="needs_investigation",
            priority="high",
            recommended_next_step="investigate",
            rationale="test",
        ),
        enrichment=EnrichmentResult(
            confidence="low",
            notes="test",
        ),
        risk_context="low",
    )


@pytest.mark.asyncio
async def test_agent_triage_includes_mcp_fields_when_mocked(test_settings: Settings) -> None:
    classification = AlertClassificationResult(
        track="security",
        recommended_pipeline="security",
        confidence=0.9,
        reason="failed login pattern",
        signals=["auth"],
    )
    mcp_context = McpAlertContext(metadata_hosts=["web-prod-01"])
    body = {
        "normalized": {"host": "web-prod-01", "user": "jdoe", "failed": "login"},
        "search_name": "Suspicious auth failed login alert",
        "users": [{"user_id": "jdoe", "risk_score": "3", "department": "IT"}],
        "assets": [
            {
                "asset_id": "srv-web-01",
                "hostname": "web-prod-01",
                "ip": "10.0.0.5",
                "criticality": "high",
                "risk_score": "4",
            }
        ],
        "relationships": [
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
            }
        ],
    }

    settings = test_settings.model_copy(
        update={
            "tsoc_mcp_enabled": True,
            "splunk_mcp_token": "test-token",
            "splunk_mcp_url": "https://splunk.test:8089/services/mcp",
        }
    )

    async def _fake_spl(*_a, **_k):
        return (
            RootCauseSpl(
                spl='search index=main host="web-prod-01" earliest=-24h@h latest=now | stats count by user',
                explanation="Stub SPL for triage test.",
            ),
            "rule_based",
        )

    def _override() -> Settings:
        return settings

    app.dependency_overrides[get_settings] = _override
    try:
        with patch(
            "services.alert.agent_triage.classify_with_optional_mcp",
            new_callable=AsyncMock,
            return_value=(classification, mcp_context, True),
        ):
            with patch(
                "services.alert.agent_triage.run_analysis",
                new_callable=AsyncMock,
                return_value=_minimal_soc_result(),
            ):
                with patch(
                    "services.alert.agent_triage.suggest_spl_for_alert",
                    new_callable=AsyncMock,
                    side_effect=_fake_spl,
                ):
                    with patch(
                        "services.alert.agent_triage.persist_agentic_ops_route_to_splunk",
                        new_callable=AsyncMock,
                    ):
                        with TestClient(app) as client:
                            r = client.post("/api/v1/agents/triage", json=body)
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    data = r.json()
    assert data.get("mcp_used") is True
    assert data.get("track") == "security"
