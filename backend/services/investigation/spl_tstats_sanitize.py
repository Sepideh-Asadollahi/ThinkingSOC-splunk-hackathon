"""Normalize investigation SPL drafts (``search`` only — no tstats/datamodel)."""

from __future__ import annotations


def sanitize_spl_draft(spl: str) -> str:
    """Generic syntax cleanup only; semantic fixes use Splunk parser + LLM refine."""
    from services.investigation.spl_syntax_sanitize import sanitize_spl_syntax

    return sanitize_spl_syntax(spl)


def normalize_tstats_spl(spl: str) -> str:
    """Deprecated alias — returns sanitized search SPL (no tstats conversion)."""
    return sanitize_spl_draft(spl)


def spl_parser_app(settings) -> str:
    return getattr(settings, "tsoc_spl_parser_app", None) or "search"


def spl_execute_app(settings, spl: str) -> str:
    """App namespace for oneshot execution."""
    return getattr(settings, "tsoc_splunk_app", None) or "search"
