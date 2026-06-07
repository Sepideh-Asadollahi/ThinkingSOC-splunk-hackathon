"""SAIA / MCP prompt limits and default instruction text."""

from __future__ import annotations

# Splunk MCP Server 1.1.2 ``saia_generate_spl`` schema: prompt max 1000 chars.
SAIA_MCP_PROMPT_MAX = 1000

SAIA_SPL_INSTRUCTION = (
    "Write simple Splunk SPL to answer the question (prefer search). "
    "No tstats, datamodel, or complex commands: join, append, transaction, map, multisearch, union."
)
