"""Tests for investigation question post-processing."""

from __future__ import annotations

from services.investigation.investigation_question_context import (
    condense_investigation_question,
    enrich_question_with_alert_fields,
    merge_alert_field_sample,
    postprocess_investigation_question_strings,
    primary_alert_fields,
    strip_time_phrases_from_question,
)
from services.soc_analysis.fallback_questions import fallback_investigation_questions


def test_strip_time_phrases() -> None:
    q = "On host=h1, what ran in the last 24 hours with earliest=-1h latest=now?"
    out = strip_time_phrases_from_question(q)
    assert "earliest" not in out.lower()
    assert "last 24" not in out.lower()
    assert "host=h1" in out or "h1" in out


def test_condense_splits_compound_question() -> None:
    q = "What is ParentImage for Image=x?; also list all network connections and users"
    out = condense_investigation_question(q)
    assert "network" not in out.lower()
    assert out.endswith("?")


def test_enrich_rewrites_parent_question() -> None:
    fields = [("host", "web-01"), ("Image", "evil.exe")]
    out = enrich_question_with_alert_fields("What is the parent process?", fields)
    assert "web-01" in out or "evil.exe" in out
    assert out.endswith("?")
    assert "(alert fields:" not in out


def test_fallback_single_answer_templates() -> None:
    qs = fallback_investigation_questions(
        {"host": "h1", "Image": "cmd.exe"},
        [],
        max_items=3,
    )
    assert len(qs) >= 1
    assert all(q.endswith("?") for q in qs)
    assert all("h1" in q or "cmd.exe" in q for q in qs)
    assert len({q.split(" for ", 1)[0] for q in qs if " for " in q}) >= 1


def test_fallback_uses_distinct_fields_from_alert() -> None:
    qs = fallback_investigation_questions(
        {
            "host": "dc-01",
            "user": "svc_backup",
            "src_ip": "8.8.8.8",
        },
        [],
        max_items=3,
    )
    assert len(qs) >= 2
    assert all("dc-01" in q or "svc_backup" in q or "8.8.8.8" in q for q in qs)
    assert len(qs) == len(set(qs))


def test_enrich_keeps_existing_field_reference() -> None:
    fields = [("host", "web-01"), ("Image", "cmd.exe")]
    q = "On host=web-01, what is ParentImage for Image=cmd.exe?"
    out = enrich_question_with_alert_fields(q, fields)
    assert out == strip_time_phrases_from_question(q)
    assert "(alert fields:" not in out


def test_merge_orig_search_fields() -> None:
    sample = merge_alert_field_sample(
        {"orig_search": 'search index=botsv1 host=desk01 Image="evil.exe"'},
        None,
    )
    fields = primary_alert_fields(sample)
    names = {k for k, _ in fields}
    assert "index" in names or any(v == "botsv1" for _, v in fields)
    assert "host" in names or any("desk01" in v for _, v in fields)


def test_postprocess_strips_time_and_enriches() -> None:
    norm = {"host": "srv1", "Image": "a.exe", "user": "bob"}
    out = postprocess_investigation_question_strings(
        ["List lateral movement in the past 2 hours"],
        normalized=norm,
        max_items=3,
    )
    assert len(out) == 1
    assert "srv1" in out[0] or "host=" in out[0]
    assert "past 2 hours" not in out[0].lower()
    assert len(out[0]) <= 220
