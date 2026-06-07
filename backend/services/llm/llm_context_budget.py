"""Prompt size budgets derived from ``TSOC_LLM_CONTEXT_TOKENS`` (default 128k)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import Settings

# Rough chars/token for JSON + SPL (conservative vs English prose).
_CHARS_PER_TOKEN = 3.5
# Reserve completion + system overhead inside the context window.
_RESERVED_OUTPUT_TOKENS = 8192


def context_input_char_budget(settings: "Settings") -> int:
    """Approximate max input characters for one LLM call."""
    tokens = int(getattr(settings, "tsoc_llm_context_tokens", 131072) or 131072)
    input_tokens = max(4096, tokens - _RESERVED_OUTPUT_TOKENS)
    return int(input_tokens * _CHARS_PER_TOKEN)


def clamp_text(text: str, max_chars: int) -> str:
    if not text or max_chars <= 0:
        return text or ""
    return text[:max_chars]


def schema_prompt_max_chars(settings: "Settings") -> int:
    """CIM schema block size for SAIA / SPL LLM (fraction of 128k input budget)."""
    cap = int(getattr(settings, "tsoc_cim_schema_prompt_max_chars", 0) or 0)
    budget = int(context_input_char_budget(settings) * 0.45)
    if cap > 0:
        return min(cap, budget) if budget > 0 else cap
    return budget or 98304


def alert_context_max_chars(settings: "Settings") -> int:
    """Alert JSON / canonical snippet in per-question SPL prompts."""
    cap = int(getattr(settings, "tsoc_spl_alert_context_max_chars", 0) or 0)
    budget = int(context_input_char_budget(settings) * 0.12)
    if cap > 0:
        return min(cap, budget) if budget > 0 else cap
    return budget or 32768


def saia_aux_context_max_chars(settings: "Settings") -> int:
    """SAIA additional_context / alert field caps."""
    return min(alert_context_max_chars(settings), 65536)


def saia_mcp_prompt_max_chars(settings: "Settings") -> int:
    """Splunk MCP ``saia_generate_spl`` prompt field (schema max 1000)."""
    return min(1000, int(getattr(settings, "tsoc_saia_mcp_prompt_max_chars", 1000) or 1000))
