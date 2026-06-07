# LLM Service

Unified LLM integration layer. Wraps LiteLLM for provider-agnostic chat completions, manages context budgets, extracts thinking/reasoning content from model responses, and provides full-length trace logging for MCP and SAIA calls.

## Key files

| File | Description |
|------|-------------|
| `litellm_service.py` | LiteLLM-backed chat/completion — single integration point for all LLM providers |
| `llm_context_budget.py` | Prompt size budgets derived from configurable context window tokens |
| `thinking_content.py` | Splits reasoning/thinking blocks from final model answers |
| `full_trace_log.py` | Full-length trace logging for Splunk MCP JSON-RPC and SAIA tool calls |

## Related docs

- [LLM Service Layer](../../../docs/18-llm-service-layer.md)
