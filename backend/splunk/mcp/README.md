<!-- folder-readme: auto -->
# backend/splunk/mcp

Parent: [README.md](../README.md)

Splunk MCP JSON-RPC client (`/services/mcp`).

## Contents

- `__init__.py`
- `client.py`
- `context_builder.py` — classification/triage MCP metadata
- `hunter_judge_context.py` — Hunter hunt queries + Judge SAIA/verification before LLM stages
- `errors.py`
- `spl_assistant.py` — backward-compatible re-exports
- `saia/` — SAIA generate/optimize/explain (`constants`, `prompt`, `parse`, `tools`, `pipeline`)
- `tool_registry.py`

## See also

- [README.md](../README.md)
- [05-codebase-map.md](../../docs/05-codebase-map.md)
