"""SPL draft normalization (search-only policy)."""

from __future__ import annotations

from services.investigation.spl_tstats_sanitize import normalize_tstats_spl, sanitize_spl_draft, spl_parser_app


def test_sanitize_spl_draft_keeps_search() -> None:
    raw = 'search index=botsv1 host=we8105desk | stats count by User'
    out = sanitize_spl_draft(raw)
    assert "search index=botsv1" in out
    assert "stats count" in out


def test_normalize_tstats_alias_collapses_whitespace() -> None:
    raw = 'search   index=botsv1   |   stats count'
    out = normalize_tstats_spl(raw)
    assert out == 'search index=botsv1 | stats count'


def test_sanitize_strips_leading_pipe_before_search() -> None:
    raw = "| search index=main | head 10"
    out = sanitize_spl_draft(raw)
    assert out.startswith("search index=main")


def test_parser_app_is_search(test_settings) -> None:
    assert spl_parser_app(test_settings) == "search"


def test_sanitize_fixes_trailing_backslash_in_quoted_path() -> None:
    raw = (
        'search index=botsv1 Image="C:\\Windows\\System32\\osk.exe\\" '
        '| stats count'
    )
    out = sanitize_spl_draft(raw)
    assert 'Image="C:/Windows/System32/osk.exe"' in out
    assert "stats count" in out


def test_sanitize_normalizes_windows_path_backslashes() -> None:
    raw = 'search index=main host=desk Image="C:\\Users\\Public\\invoke.ps1"'
    out = sanitize_spl_draft(raw)
    assert "C:/Users/Public/invoke.ps1" in out
    assert "C:\\Users" not in out
