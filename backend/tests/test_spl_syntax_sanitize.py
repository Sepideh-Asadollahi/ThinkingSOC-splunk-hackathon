"""Generic SPL syntax sanitization tests."""

from __future__ import annotations

from services.investigation.spl_syntax_sanitize import (
    dedupe_search_field_clauses,
    quote_spl_colon_field_values,
    sanitize_spl_syntax,
    strip_spl_backticks,
)


def test_quote_any_colon_field_value() -> None:
    raw = "search index=main custom=Foo:Bar:Baz host=h1"
    out = quote_spl_colon_field_values(raw)
    assert 'custom="Foo:Bar:Baz"' in out


def test_dedupe_all_search_fields() -> None:
    raw = (
        "search index=botsv1 source=WinEventLog:Sysmon source=WinEventLog:Other "
        "index=wrong host=h1 | stats count"
    )
    out = dedupe_search_field_clauses(raw)
    assert out.count("source=") == 1
    assert "index=wrong" not in out
    assert "index=botsv1" in out


def test_sanitize_fixes_missing_search_and_by_field_eq() -> None:
    raw = "index=firewall | stats count by index=firewall"
    out = sanitize_spl_syntax(raw)
    assert out.startswith("search index=firewall")
    assert "by index" in out
    assert "by index=firewall" not in out


def test_sanitize_fixes_table_field_eq_args() -> None:
    raw = 'search index=firewall | table index=firewall host'
    out = sanitize_spl_syntax(raw)
    assert "| table index host" in out
    assert "index=firewall" not in out.split("|", 1)[1]


def test_sanitize_fixes_llm_markdown_and_duplicates() -> None:
    raw = (
        'search index=wineventlog sourcetype=`"XmlWinEventLog:Microsoft-Windows-Sysmon/Operational`" '
        'and source="WinEventLog:Microsoft-Windows-Sysmon/Operational" '
        'source="WinEventLog:Microsoft-Windows-Sysmon/Operational" EventID=3 host=DESKTOP-BRUCE '
        '| stats count'
    )
    out = sanitize_spl_syntax(raw)
    assert "`" not in out
    assert out.count('source="WinEventLog:Microsoft-Windows-Sysmon/Operational"') == 1
    assert 'sourcetype="XmlWinEventLog:Microsoft-Windows-Sysmon/Operational"' in out
    assert " and " not in out
    # EventID / index typos are LLM+parser refine — not hardcoded here
    assert "EventID=3" in out
