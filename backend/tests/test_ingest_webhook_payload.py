"""Webhook payload shape logging."""

from __future__ import annotations

import logging

from models.handoff import SplunkAlertIngest, normalize_splunk_ingest_payload
from services.alert.ingest_webhook_payload import (
    log_ingest_webhook_payload,
    log_raw_webhook_body,
    serialize_webhook_raw_body,
    summarize_webhook_payload,
)


def test_summarize_webhook_single_result_object() -> None:
    raw = {
        "sid": "scheduler__admin__search__foo_at_1",
        "search_name": "New TesT",
        "result": {"Computer": "desk", "User": "bob", "_time": "2018-08-24 21:18:41"},
    }
    summary = summarize_webhook_payload(raw)
    assert summary["has_result_object"] is True
    assert summary["results_array_len"] == 0
    assert "Computer" in summary["result_field_keys"]
    assert "desk" in summary["result_preview"]


def test_summarize_webhook_results_array() -> None:
    raw = {
        "sid": "job.1",
        "results": [{"a": 1}, {"a": 2}],
    }
    summary = summarize_webhook_payload(raw)
    assert summary["results_array_len"] == 2
    assert summary["has_result_object"] is False


def test_serialize_webhook_raw_body_no_truncation() -> None:
    raw = {
        "sid": "scheduler__admin__search__foo_at_1",
        "search_name": "New TesT",
        "result": {"Computer": "we8105desk", "User": "bob", "note": "x" * 5000},
    }
    text = serialize_webhook_raw_body(raw)
    assert "x" * 5000 in text
    assert "we8105desk" in text


def test_log_raw_webhook_body_full_json(caplog) -> None:
    caplog.set_level(logging.INFO)
    raw = {
        "sid": "job.1",
        "search_name": "demo",
        "result": {"host": "h1"},
        "app": "ThinkingSOC_Hackathon",
    }
    log_raw_webhook_body(stage="webhook_received", raw_body=raw)
    messages = [r.getMessage() for r in caplog.records]
    assert any("ingest_webhook_raw_json" in m and '"host": "h1"' in m for m in messages)
    assert any("ingest_webhook_raw_pretty" in m and "ThinkingSOC_Hackathon" in m for m in messages)


def test_log_webhook_payload_includes_result_preview(caplog) -> None:
    caplog.set_level(logging.INFO)
    raw = {
        "sid": "scheduler__admin__search__foo_at_1",
        "search_name": "New TesT",
        "result": {"Computer": "we8105desk", "User": "bob"},
    }
    handoff = normalize_splunk_ingest_payload(raw)
    log_ingest_webhook_payload(stage="webhook_received", raw_body=raw, handoff=handoff)
    messages = [r.getMessage() for r in caplog.records]
    assert any("ingest_webhook_payload" in m and "has_result_object=True" in m for m in messages)
    assert any("splunk_result_object_preview" in m and "we8105desk" in m for m in messages)
    assert any("handoff_row_preview" in m for m in messages)
