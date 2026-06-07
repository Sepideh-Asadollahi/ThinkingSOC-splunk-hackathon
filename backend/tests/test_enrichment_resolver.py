"""Unit tests for inventory enrichment (no Splunk)."""

from __future__ import annotations

from services.alert.enrichment_resolver import enrich_from_inventory


def _sample_tables():
    users = [
        {"user_id": "u1", "risk_score": "3"},
        {"user_id": "u2", "risk_score": "2"},
    ]
    assets = [
        {"asset_id": "a1", "hostname": "host-a", "ip": "10.0.0.1", "criticality": "high"},
        {"asset_id": "a2", "hostname": "host-b", "ip": "10.0.0.2", "criticality": "low"},
    ]
    relationships = [
        {
            "relationship_id": "rel-u2-a1",
            "user_id": "u2",
            "asset_id": "a1",
        },
    ]
    return users, assets, relationships


def test_resolve_host_and_user():
    users, assets, relationships = _sample_tables()
    out = enrich_from_inventory({"host": "host-a", "user": "u2"}, users, assets, relationships)
    assert out.resolved_asset_id == "a1"
    assert out.resolved_user_id == "u2"
    assert out.confidence in ("high", "medium")


def test_no_match_note():
    users, assets, relationships = _sample_tables()
    out = enrich_from_inventory({"host": "unknown"}, users, assets, relationships)
    assert out.resolved_asset_id is None
    assert out.resolved_user_id is None
    assert out.confidence == "low"
    assert "inventory" in out.notes.lower()


def test_highest_criticality_pick():
    users: list = []
    assets = [
        {"asset_id": "low", "ip": "10.1.1.1", "criticality": "low"},
        {"asset_id": "high", "ip": "10.1.1.1", "criticality": "high"},
    ]
    out = enrich_from_inventory({"src": "10.1.1.1"}, users, assets, [])
    assert out.resolved_asset_id == "high"
    assert out.confidence == "medium"


def test_relationship_links_user_when_only_asset_matched():
    users, assets, relationships = _sample_tables()
    out = enrich_from_inventory({"host": "host-a"}, users, assets, relationships)
    assert out.resolved_asset_id == "a1"
    assert out.resolved_user_id == "u2"
    assert "rel-u2-a1" in out.matched_relationship_ids
    assert "relationship" in out.notes.lower()


def test_relationship_links_asset_when_only_user_matched():
    users, assets, relationships = _sample_tables()
    out = enrich_from_inventory({"user": "u2"}, users, assets, relationships)
    assert out.resolved_user_id == "u2"
    assert out.resolved_asset_id == "a1"
    assert "rel-u2-a1" in out.matched_relationship_ids


def test_relationship_does_not_override_both_sides_already_matched():
    users, assets, relationships = _sample_tables()
    out = enrich_from_inventory({"host": "host-a", "user": "u1"}, users, assets, relationships)
    assert out.resolved_asset_id == "a1"
    assert out.resolved_user_id == "u1"
    assert out.matched_relationship_ids == []


def test_relationship_picks_highest_criticality_asset_for_user():
    users = [{"user_id": "u1", "risk_score": "1"}]
    assets = [
        {"asset_id": "low-a", "hostname": "x", "criticality": "low"},
        {"asset_id": "crit-a", "hostname": "y", "criticality": "critical"},
    ]
    relationships = [
        {"relationship_id": "rel-1", "user_id": "u1", "asset_id": "low-a"},
        {"relationship_id": "rel-2", "user_id": "u1", "asset_id": "crit-a"},
    ]
    out = enrich_from_inventory({"user": "u1"}, users, assets, relationships)
    assert out.resolved_asset_id == "crit-a"
    assert "rel-2" in out.matched_relationship_ids


def test_relationship_picks_highest_risk_user_for_asset():
    users = [
        {"user_id": "low-u", "risk_score": "1"},
        {"user_id": "high-u", "risk_score": "9"},
    ]
    assets = [{"asset_id": "a1", "hostname": "host-z", "criticality": "medium"}]
    relationships = [
        {"relationship_id": "rel-low", "user_id": "low-u", "asset_id": "a1"},
        {"relationship_id": "rel-high", "user_id": "high-u", "asset_id": "a1"},
    ]
    out = enrich_from_inventory({"host": "host-z"}, users, assets, relationships)
    assert out.resolved_user_id == "high-u"
    assert "rel-high" in out.matched_relationship_ids


