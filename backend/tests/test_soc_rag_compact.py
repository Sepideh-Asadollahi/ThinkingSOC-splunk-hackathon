"""Tests for RAG compact document builder."""

from services.soc_rag.compact_alert import compact_alert_document, extract_essential_fields


def test_extract_essential_strips_raw_and_secrets() -> None:
    merged = {
        "_time": "2026-05-16T12:00:00Z",
        "user": "alice",
        "_raw": "huge raw event",
        "password": "secret",
        "signature": "Failed login",
    }
    essential = extract_essential_fields(merged)
    assert "alice" in essential.values()
    assert "_raw" not in essential
    assert "password" not in essential


def test_compact_alert_document_shape() -> None:
    doc = compact_alert_document(
        sid="sid-test-1",
        search_name="Suspicious login",
        normalized={"user": "alice", "severity": "high"},
        splunk_results=[{"src": "203.0.113.1"}],
    )
    assert doc.doc_id.endswith("::0")
    assert doc.doc_type == "splunk_alert"
    assert doc.essential.get("user") == "alice"
    assert "Failed" not in doc.chunk_text or "alice" in doc.chunk_text
    assert len(doc.summary_line) > 5
