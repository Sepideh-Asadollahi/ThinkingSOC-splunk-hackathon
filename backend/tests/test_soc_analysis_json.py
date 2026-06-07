"""LLM JSON response parsing."""

from __future__ import annotations

import json

import pytest

from services.soc_analysis.soc_analysis_json import (
    parse_llm_json_response,
    salvage_hunter_json_from_text,
    salvage_investigation_questions_from_text,
)


def test_parse_plain_json() -> None:
    data = parse_llm_json_response('{"spl": "| search *", "pivots": []}')
    assert data["spl"] == "| search *"


def test_parse_fenced_json() -> None:
    raw = """Some intro
```json
{"spl": "| tstats count", "notes": []}
```
"""
    data = parse_llm_json_response(raw)
    assert "tstats" in data["spl"]


def test_parse_prose_then_json_object() -> None:
    raw = """But join syntax: need subsearch.
We can do:
| tstats count
Now produce JSON.
{"spl": "| search index=botsv1", "explanation": "ok", "time_window": "earliest=-5m latest=+5m", "pivots": ["host"], "notes": []}
"""
    data = parse_llm_json_response(raw)
    assert data["spl"] == "| search index=botsv1"
    assert data["time_window"] == "earliest=-5m latest=+5m"


def test_parse_empty_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_llm_json_response("")


def test_salvage_hunter_spl_lines() -> None:
    raw = (
        'index=botsv1 sourcetype="XmlWinEventLog:Microsoft-Windows-Sysmon/Operational" '
        'host=we8105desk EventCode=3 earliest=-48h | stats count by DestinationIp\n'
        'index=botsv1 host=we8105desk EventCode=10 earliest=-48h | table _time Image'
    )
    data = salvage_hunter_json_from_text(raw)
    assert data is not None
    assert len(data["splunk_search_suggestions"]) == 2
    assert "index=botsv1" in data["splunk_search_suggestions"][0]


def test_salvage_investigation_questions_from_reasoning() -> None:
    raw = (
        "Planning five questions.\n"
        '{"investigation_questions": ["What is host=we8105desk EventCode=10 count?", '
        '"What is Image=C:\\\\Windows\\\\System32\\\\osk.exe parent activity?"]}'
    )
    data = salvage_investigation_questions_from_text(raw)
    assert data is not None
    assert len(data["investigation_questions"]) == 2


def test_parse_recover_bare_hunter_spl() -> None:
    raw = (
        "index=botsv1 host=we8105desk EventCode=1 earliest=-48h | stats count by Image\n"
        "index=botsv1 host=we8105desk EventCode=11 earliest=-48h | table TargetFilename"
    )
    data = parse_llm_json_response(raw)
    assert data["splunk_search_suggestions"]
    assert "recovered" in str(data.get("notes", [])).lower()
