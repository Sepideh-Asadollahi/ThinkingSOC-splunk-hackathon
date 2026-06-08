"""Agent triage must not persist soc_analysis twice (run_analysis already persists)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from models.agents import AgentTriageRequest
from models.agentic_ops import AlertClassificationResult
from models.analysis import HunterSection, JudgeVerdict, RootCauseSpl, SocAnalysisResult
from models.enrichment import EnrichmentResult
from services.alert.agent_triage import run_agent_triage


def _classification() -> AlertClassificationResult:
    return AlertClassificationResult(
        track="security",
        recommended_pipeline="security",
        confidence=0.9,
        classification_source="rules",
        needs_human_routing=False,
        reason="test",
    )


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
        enrichment=EnrichmentResult(confidence="low", notes="test"),
        risk_context="low",
    )


@pytest.mark.asyncio
async def test_run_agent_triage_does_not_persist_soc_analysis_twice(test_settings: Settings) -> None:
    body = AgentTriageRequest(
        sid="scheduler__admin__search__job_at_1",
        search_name="New TesT",
        normalized={"host": "desk"},
        splunk_results=[{"ParentImage": "row1.exe"}],
    )

    with (
        patch(
            "services.alert.agent_triage.load_inventory_tables",
            new_callable=AsyncMock,
            return_value=([], [], []),
        ),
        patch(
            "services.alert.agent_triage.classify_with_optional_mcp",
            new_callable=AsyncMock,
            return_value=(_classification(), None, False),
        ),
        patch(
            "services.alert.agent_triage.run_analysis",
            new_callable=AsyncMock,
            return_value=_minimal_soc_result(),
        ),
        patch(
            "services.alert.agent_triage.suggest_spl_for_alert",
            new_callable=AsyncMock,
            return_value=(RootCauseSpl(spl="index=main", rationale="test"), "rule_based"),
        ),
        patch(
            "services.alert.agent_triage.persist_agentic_ops_route_to_splunk",
            new_callable=AsyncMock,
        ),
        patch(
            "services.splunk_json_store.persist_soc_analysis_to_splunk",
            new_callable=AsyncMock,
        ) as persist_soc,
    ):
        await run_agent_triage(test_settings, body)

    persist_soc.assert_not_awaited()
