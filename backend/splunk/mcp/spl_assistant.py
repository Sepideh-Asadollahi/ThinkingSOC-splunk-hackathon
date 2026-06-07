"""SPL via Splunk MCP: generate → optimize → explain (Splunk AI Assistant).

Implementation lives in ``splunk.mcp.saia``; this module re-exports the public API
and legacy private names used by tests and ``spl_mcp_review``.
"""

from __future__ import annotations

from .saia import (
    SAIA_MCP_PROMPT_MAX,
    SAIA_SPL_INSTRUCTION,
    build_saia_generate_args,
    call_saia_explain,
    call_saia_generate,
    call_saia_optimize,
    extract_spl_from_saia_text,
    generate_spl_via_mcp,
    parse_saia_spl_result,
)

# Legacy private aliases (tests, spl_mcp_review)
_SAIA_MCP_PROMPT_MAX = SAIA_MCP_PROMPT_MAX
_SAIA_SPL_INSTRUCTION = SAIA_SPL_INSTRUCTION
_extract_spl_from_saia_text = extract_spl_from_saia_text
_parse_saia_spl_result = parse_saia_spl_result
_call_saia_generate = call_saia_generate
_call_saia_optimize = call_saia_optimize
_call_saia_explain = call_saia_explain

__all__ = [
    "SAIA_MCP_PROMPT_MAX",
    "SAIA_SPL_INSTRUCTION",
    "_SAIA_MCP_PROMPT_MAX",
    "_SAIA_SPL_INSTRUCTION",
    "_call_saia_explain",
    "_call_saia_generate",
    "_call_saia_optimize",
    "_extract_spl_from_saia_text",
    "_parse_saia_spl_result",
    "build_saia_generate_args",
    "generate_spl_via_mcp",
]
