"""SAIA SPL review is enabled by default and records unavailable when MCP is off."""

from __future__ import annotations

import pytest

from config import Settings
from models.analysis import InvestigationQuestionItem
from services.investigation.spl_saia_analysis import (
    analyze_investigation_spl_with_saia,
    enrich_investigation_item_with_saia,
    saia_spl_review_requested,
)


def test_saia_review_requested_defaults_true(test_settings: Settings) -> None:
    assert saia_spl_review_requested(test_settings) is True


@pytest.mark.asyncio
async def test_analyze_returns_unavailable_when_mcp_not_configured(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={
            "tsoc_mcp_enabled": False,
            "splunk_mcp_url": None,
            "splunk_mcp_token": None,
        }
    )
    spl, expl, analysis = await analyze_investigation_spl_with_saia(
        settings,
        spl="search index=main | head 5",
        explanation="draft",
    )
    assert spl == "search index=main | head 5"
    assert analysis is not None
    assert analysis.unavailable_reason
    assert "MCP not configured" in analysis.unavailable_reason


@pytest.mark.asyncio
async def test_enrich_always_attaches_saia_when_review_on(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={
            "tsoc_mcp_enabled": False,
            "splunk_mcp_url": None,
            "splunk_mcp_token": None,
        }
    )
    item = InvestigationQuestionItem(question="Q?", spl="search index=main")
    out = await enrich_investigation_item_with_saia(settings, item)
    assert out.spl_saia_analysis is not None
    assert out.spl_saia_analysis.unavailable_reason
