"""Risk context built from enrichment + inventory rows (relationship-aware)."""

from __future__ import annotations

import pytest

from models.enrichment import EnrichmentResult
from services.alert.enrichment_resolver import enrich_from_inventory
from services.soc_analysis.soc_analysis_risk import build_risk_context, find_asset_row, find_user_row


def test_build_risk_context_includes_asset_and_user_scores():
    enrichment = EnrichmentResult(
        resolved_user_id="u1",
        resolved_asset_id="a1",
        confidence="high",
        notes="Matched",
    )
    user = {"user_id": "u1", "risk_score": "7", "department": "IT"}
    asset = {"asset_id": "a1", "criticality": "critical", "risk_score": "9"}
    text = build_risk_context(enrichment, user, asset)
    assert "criticality=critical" in text
    assert "risk_score=9" in text
    assert "User u1" in text
    assert "department=IT" in text


def test_build_risk_context_after_relationship_link():
    users = [{"user_id": "u2", "risk_score": "5", "department": "Finance"}]
    assets = [
        {"asset_id": "a1", "hostname": "host-a", "criticality": "high", "risk_score": "8"},
    ]
    relationships = [{"relationship_id": "rel-1", "user_id": "u2", "asset_id": "a1"}]
    enrichment = enrich_from_inventory({"host": "host-a"}, users, assets, relationships)
    urow = find_user_row(users, enrichment.resolved_user_id)
    arow = find_asset_row(assets, enrichment.resolved_asset_id)
    text = build_risk_context(enrichment, urow, arow)
    assert enrichment.resolved_user_id == "u2"
    assert "criticality=high" in text
    assert "risk_score=5" in text or "User u2" in text


def test_build_risk_context_unknown_inventory_rows():
    enrichment = EnrichmentResult(
        resolved_user_id="ghost-user",
        resolved_asset_id="ghost-asset",
        confidence="medium",
        notes="Linked via relationship only",
        matched_relationship_ids=["rel-x"],
    )
    text = build_risk_context(enrichment, None, None)
    assert "ghost-user" in text
    assert "ghost-asset" in text
    assert "not found" in text.lower()


@pytest.mark.asyncio
async def test_run_analysis_risk_via_relationship_only(
    test_settings, force_soc_analysis_langgraph_fallback
):
    """SOC pipeline: alert matches asset only; user + risk come from relationship."""
    from models.analysis import AnalysisRunRequest
    from services.soc_analysis import run_analysis

    s = test_settings
    users = [{"user_id": "jdoe", "risk_score": "6", "department": "IT"}]
    assets = [
        {
            "asset_id": "srv-web-01",
            "hostname": "web-prod-01",
            "criticality": "high",
            "risk_score": "4",
        },
    ]
    relationships = [
        {"relationship_id": "rel-jdoe-web", "user_id": "jdoe", "asset_id": "srv-web-01"},
    ]
    out = await run_analysis(
        s,
        AnalysisRunRequest(normalized={"host": "web-prod-01"}, search_name="rel-risk-test"),
        users=users,
        assets=assets,
        relationships=relationships,
    )
    assert out.enrichment.resolved_asset_id == "srv-web-01"
    assert out.enrichment.resolved_user_id == "jdoe"
    assert "rel-jdoe-web" in out.enrichment.matched_relationship_ids
    assert out.risk_context
    assert "criticality=high" in out.risk_context
    assert "jdoe" in out.risk_context
