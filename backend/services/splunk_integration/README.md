# Splunk Integration Service

Splunk integration layer providing the AI Assistant SPL generation interface and MCP service orchestration (status, health, SAIA availability checks).

## Key files

| File | Description |
|------|-------------|
| `splunk_ai_assistant.py` | Generates analyst-ready SPL via REST `/predict`, LiteLLM, or rule-based fallback |
| `splunk_mcp_service.py` | Orchestration helpers for Splunk MCP (status, health, SAIA availability) |

## Related docs

- [Integration Boundaries](../../../docs/02-integration-boundaries.md)
- [Splunk MCP Tool Layer](../../../docs/15-splunk-mcp-tool-layer.md)
