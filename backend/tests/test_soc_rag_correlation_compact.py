"""Unit tests for correlation RAG document compaction."""

from __future__ import annotations

from services.soc_rag.compact_correlation import (
    DOC_TYPE_FINDING,
    compact_attack_path_document,
    compact_finding_document,
    compact_graph_alert_document,
)


def test_compact_finding_document_includes_alerts() -> None:
    doc = compact_finding_document(
        finding_id="f-1",
        display_id="FIND-001",
        finding_type="smart_attack_discovery",
        title="Lateral movement cluster",
        summary="Three alerts linked by shared user",
        risk_score=85,
        ticket_status="open",
        owner="unassigned",
        details={
            "incident_id": "inc-abc",
            "executive_summary": "Coordinated activity across VPN and endpoint.",
            "contributing_alerts": [
                {
                    "alert_row_id": "alert-1",
                    "alert_name": "Suspicious login",
                    "sid": "sid-1",
                    "risk_score": 70,
                    "threat_status": "open",
                }
            ],
            "key_entities": {"identities": ["username:alice"], "assets": ["hostname:ws-01"]},
            "attack_analysis_steps": [
                {
                    "phase_label": "Initial Access",
                    "description": "alice authenticated from an unusual VPN endpoint.",
                }
            ],
        },
    )
    assert doc.doc_type == DOC_TYPE_FINDING
    assert "alert-1" in doc.chunk_text
    assert "username:alice" in doc.chunk_text
    assert "Step 1:" in doc.chunk_text
    assert "Initial Access" in doc.chunk_text
    assert doc.doc_id == "corr-finding:f-1"


def test_compact_graph_alert_document() -> None:
    doc = compact_graph_alert_document(
        alert_row_id="row-99",
        props={
            "name": "PowerShell execution",
            "sid": "scheduler__x",
            "search_name": "TSOC powershell",
            "risk_score": 72,
            "status": "open",
            "timestamp": "2026-05-20T10:00:00Z",
        },
        related_entities=["username:bob", "hostname:dc-01"],
    )
    assert "row-99" in doc.chunk_text
    assert "username:bob" in doc.chunk_text


def test_compact_attack_path_document() -> None:
    doc = compact_attack_path_document(
        from_alert_id="a1",
        to_alert_id="a2",
        narrative="User credential use followed by lateral movement",
        time_delta_seconds=120,
    )
    assert "CAUSED" in doc.chunk_text
    assert "a1" in doc.chunk_text and "a2" in doc.chunk_text
