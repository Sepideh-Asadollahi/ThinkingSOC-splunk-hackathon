"""Tests for Splunk result → LLM alert_fields flattening."""

from services.alert.alert_fields import build_alert_fields_for_llm


def test_build_alert_fields_includes_search_name_and_all_result_keys() -> None:
    row = {
        "_time": "2026-05-16T10:15:00.000Z",
        "host": "dc-01.corp.example",
        "src": "203.0.113.45",
        "dest": "dc-01.corp.example",
        "user": "svc_backup",
        "severity": "high",
        "signature": "Possible brute force",
        "signature_id": "T1110",
        "count": "47",
    }
    fields = build_alert_fields_for_llm(
        search_name="Brute Force - Failed Logins",
        normalized={},
        splunk_results_preview=[row],
    )
    assert fields["search_name"] == "Brute Force - Failed Logins"
    assert fields["_time"] == row["_time"]
    assert fields["host"] == row["host"]
    assert fields["count"] == "47"
    assert fields["signature_id"] == "T1110"
    assert fields["row_index"] == 0


def test_build_alert_fields_merges_normalized_and_row() -> None:
    fields = build_alert_fields_for_llm(
        search_name="demo",
        normalized={"severity": "medium"},
        splunk_results_preview=[{"host": "web-01", "severity": "high"}],
    )
    assert fields["search_name"] == "demo"
    assert fields["host"] == "web-01"
    assert fields["severity"] == "high"
