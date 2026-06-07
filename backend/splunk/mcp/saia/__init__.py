"""Splunk AI Assistant (SAIA) via MCP — modular implementation."""

from __future__ import annotations

from .constants import SAIA_MCP_PROMPT_MAX, SAIA_SPL_INSTRUCTION
from .helpers import append_note, guess_time_window, saia_tool_args_spl
from .parse import (
    collapse_spl_lines,
    extract_spl_from_saia_text,
    looks_like_spl_text,
    parse_explain_text,
    parse_saia_spl_result,
)
from .pipeline import generate_spl_via_mcp
from .prompt import build_nl_query, build_saia_generate_args, truncate_saia_prompt
from .tools import call_saia_explain, call_saia_generate, call_saia_optimize

__all__ = [
    "SAIA_MCP_PROMPT_MAX",
    "SAIA_SPL_INSTRUCTION",
    "append_note",
    "build_nl_query",
    "build_saia_generate_args",
    "call_saia_explain",
    "call_saia_generate",
    "call_saia_optimize",
    "collapse_spl_lines",
    "extract_spl_from_saia_text",
    "generate_spl_via_mcp",
    "guess_time_window",
    "looks_like_spl_text",
    "parse_explain_text",
    "parse_saia_spl_result",
    "saia_tool_args_spl",
    "truncate_saia_prompt",
]
