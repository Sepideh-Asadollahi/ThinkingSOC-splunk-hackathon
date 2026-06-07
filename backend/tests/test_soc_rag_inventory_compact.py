"""Inventory compact docs for SOC chat."""

from services.soc_rag.compact_inventory import (
    compact_asset_document,
    compact_relationship_document,
    compact_user_document,
)


def test_compact_user_document() -> None:
    doc = compact_user_document(
        {
            "user_id": "alice",
            "display_name": "Alice",
            "department": "IT",
            "risk_score": 5,
        }
    )
    assert doc.doc_type == "inventory_user"
    assert "alice" in doc.chunk_text


def test_compact_asset_document() -> None:
    doc = compact_asset_document({"asset_id": "srv-1", "hostname": "web01", "criticality": "high"})
    assert doc.doc_type == "inventory_asset"
    assert "web01" in doc.chunk_text


def test_compact_relationship_document() -> None:
    doc = compact_relationship_document(
        {"relationship_id": "r1", "user_id": "alice", "asset_id": "srv-1"}
    )
    assert doc.doc_type == "inventory_relationship"
    assert "alice" in doc.chunk_text
