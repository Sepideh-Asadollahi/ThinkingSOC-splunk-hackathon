# mcp-mcp

## Overview

Community of 35 nodes

- **Size**: 35 nodes
- **Cohesion**: 0.2516
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| mcp_configured | Function | backend/config.py | 89-96 |
| splunk_mcp_url_for | Function | backend/config.py | 99-105 |
| McpAlertContext | Class | backend/models/mcp.py | 15-27 |
| McpStatusResponse | Class | backend/models/mcp.py | 30-37 |
| McpToolCallResponse | Class | backend/models/mcp.py | 45-47 |
| get_mcp_status | Function | backend/services/splunk_mcp_service.py | 17-50 |
| classify_with_optional_mcp | Function | backend/services/alert_mcp_enrichment.py | 14-57 |
| test_mcp_status_not_configured | Test | backend/tests/test_mcp_status.py | 14-20 |
| _load | Function | backend/tests/test_mcp_client.py | 19-21 |
| _mcp_settings | Function | backend/tests/test_mcp_client.py | 24-30 |
| test_resolve_tool_name_aliases | Test | backend/tests/test_mcp_client.py | 34-37 |
| test_mcp_client_initialize_and_list_tools | Test | backend/tests/test_mcp_client.py | 41-58 |
| test_mcp_call_tool_saia | Test | backend/tests/test_mcp_client.py | 62-80 |
| SplunkMcpClient | Class | backend/splunk/mcp/client.py | 18-157 |
| __init__ | Function | backend/splunk/mcp/client.py | 21-32 |
| _next_id | Function | backend/splunk/mcp/client.py | 34-36 |
| _headers | Function | backend/splunk/mcp/client.py | 38-43 |
| _rpc | Function | backend/splunk/mcp/client.py | 45-66 |
| initialize | Function | backend/splunk/mcp/client.py | 68-88 |
| refresh_tools | Function | backend/splunk/mcp/client.py | 90-103 |
| tool_names | Function | backend/splunk/mcp/client.py | 106-107 |
| server_info | Function | backend/splunk/mcp/client.py | 110-111 |
| ensure_ready | Function | backend/splunk/mcp/client.py | 113-115 |
| call_tool | Function | backend/splunk/mcp/client.py | 117-138 |
| call_tool_by_name | Function | backend/splunk/mcp/client.py | 140-148 |
| ping | Function | backend/splunk/mcp/client.py | 150-157 |
| _unwrap_tool_result | Function | backend/splunk/mcp/client.py | 160-178 |
| _extract_string_list | Function | backend/splunk/mcp/context_builder.py | 19-42 |
| build_mcp_alert_context | Function | backend/splunk/mcp/context_builder.py | 45-145 |
| _safe_correlation_spl | Function | backend/splunk/mcp/context_builder.py | 148-160 |
| merge_mcp_into_classification_signals | Function | backend/splunk/mcp/context_builder.py | 163-177 |
| resolve_tool_name | Function | backend/splunk/mcp/tool_registry.py | 31-37 |
| saia_tool_names | Function | backend/splunk/mcp/tool_registry.py | 40-42 |
| mcp_status_endpoint | Function | backend/api/routes/mcp.py | 28-32 |
| mcp_tool_call_endpoint | Function | backend/api/routes/mcp.py | 89-109 |

## Execution Flows

- **splunk_ingest** (criticality: 0.75, depth: 7)
- **agent_triage_endpoint** (criticality: 0.74, depth: 6)
- **mcp_spl_generate_endpoint** (criticality: 0.73, depth: 4)
- **assistant_spl_suggest** (criticality: 0.73, depth: 5)
- **run_routed_analysis_endpoint** (criticality: 0.73, depth: 4)
- **mcp_tool_call_endpoint** (criticality: 0.71, depth: 2)
- **mcp_status_endpoint** (criticality: 0.67, depth: 2)
- **__init__** (criticality: 0.43, depth: 1)
- **call_tool** (criticality: 0.38, depth: 3)
- **call_tool_by_name** (criticality: 0.38, depth: 3)
- *... and 1 more flows.*

## Dependencies

### Outgoing

- `isinstance` (26 edge(s))
- `append` (24 edge(s))
- `get` (20 edge(s))
- `str` (18 edge(s))
- `format` (17 edge(s))
- `call_tool` (7 edge(s))
- `Response` (7 edge(s))
- `strip` (6 edge(s))
- `McpToolError` (5 edge(s))
- `resolve_tool_name` (5 edge(s))
- `backend/config.py::get_settings` (3 edge(s))
- `HTTPException` (3 edge(s))
- `BaseModel` (3 edge(s))
- `warning` (3 edge(s))
- `sorted` (3 edge(s))

### Incoming

- `Response` (7 edge(s))
- `backend/tests/test_mcp_client.py` (5 edge(s))
- `backend/splunk/mcp/context_builder.py` (4 edge(s))
- `backend/models/mcp.py` (3 edge(s))
- `backend/api/routes/mcp.py` (2 edge(s))
- `backend/config.py` (2 edge(s))
- `backend/splunk/mcp/client.py` (2 edge(s))
- `backend/splunk/mcp/tool_registry.py` (2 edge(s))
- `object` (2 edge(s))
- `backend/services/splunk_ai_assistant.py::suggest_spl_for_alert` (1 edge(s))
- `backend/splunk/mcp/spl_assistant.py::generate_spl_via_mcp` (1 edge(s))
- `backend/splunk/mcp/spl_assistant.py::suggest_spl_via_mcp_for_alert` (1 edge(s))
- `backend/api/routes/mcp.py::mcp_spl_generate_endpoint` (1 edge(s))
- `backend/services/agent_triage.py::run_agent_triage` (1 edge(s))
- `backend/services/alert_mcp_enrichment.py` (1 edge(s))
