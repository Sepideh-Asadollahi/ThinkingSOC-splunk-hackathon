# devtools-classify

## Overview

Community of 38 nodes

- **Size**: 38 nodes
- **Cohesion**: 0.2933
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| AsyncTsocSdkClient | Class | backend/devtools/async_client.py | 27-122 |
| __init__ | Function | backend/devtools/async_client.py | 28-41 |
| _headers | Function | backend/devtools/async_client.py | 43-46 |
| _to_payload | Function | backend/devtools/async_client.py | 49-52 |
| _raise_api_error | Function | backend/devtools/async_client.py | 54-62 |
| _post_model | Function | backend/devtools/async_client.py | 64-90 |
| classify_alert | Function | backend/devtools/async_client.py | 92-96 |
| route_analysis | Function | backend/devtools/async_client.py | 98-102 |
| run_agent_triage | Function | backend/devtools/async_client.py | 104-108 |
| suggest_spl | Function | backend/devtools/async_client.py | 110-114 |
| mcp_status | Function | backend/devtools/async_client.py | 116-122 |
| TsocSdkClient | Class | backend/devtools/client.py | 27-121 |
| __init__ | Function | backend/devtools/client.py | 28-41 |
| _headers | Function | backend/devtools/client.py | 43-46 |
| _to_payload | Function | backend/devtools/client.py | 49-52 |
| _raise_api_error | Function | backend/devtools/client.py | 54-62 |
| _post_model | Function | backend/devtools/client.py | 64-89 |
| classify_alert | Function | backend/devtools/client.py | 91-95 |
| route_analysis | Function | backend/devtools/client.py | 97-101 |
| run_agent_triage | Function | backend/devtools/client.py | 103-107 |
| suggest_spl | Function | backend/devtools/client.py | 109-113 |
| mcp_status | Function | backend/devtools/client.py | 115-121 |
| AlertClassificationResult | Class | backend/models/agentic_ops.py | 15-23 |
| AnalysisRouteResponse | Class | backend/models/agentic_ops.py | 45-51 |
| AgentTriageResponse | Class | backend/models/agents.py | 28-37 |
| _to_text_parts | Function | backend/services/alert_classifier.py | 45-56 |
| _matched_signals | Function | backend/services/alert_classifier.py | 59-61 |
| classify_alert | Function | backend/services/alert_classifier.py | 64-123 |
| _llm_available | Function | backend/services/alert_classifier_llm.py | 26-35 |
| _should_use_llm | Function | backend/services/alert_classifier_llm.py | 38-45 |
| _parse_llm_json | Function | backend/services/alert_classifier_llm.py | 48-54 |
| _merge_classification | Function | backend/services/alert_classifier_llm.py | 57-92 |
| classify_alert_hybrid | Function | backend/services/alert_classifier_llm.py | 95-133 |
| test_classify_hybrid_skips_llm_when_confident | Test | backend/tests/test_alert_classifier_llm.py | 13-25 |
| _run | Function | backend/tests/test_alert_classifier_llm.py | 29-51 |
| test_classify_hybrid_uses_llm_when_unknown | Test | backend/tests/test_alert_classifier_llm.py | 28-53 |
| test_classify_alert_observability | Test | backend/tests/test_observability.py | 59-66 |
| test_classify_alert_security | Test | backend/tests/test_observability.py | 69-76 |

## Execution Flows

- **splunk_ingest** (criticality: 0.75, depth: 7)
- **agent_triage_endpoint** (criticality: 0.74, depth: 6)
- **run_routed_analysis_endpoint** (criticality: 0.73, depth: 4)
- **classify_alert_endpoint** (criticality: 0.71, depth: 3)
- **classify_alert** (criticality: 0.37, depth: 2)
- **route_analysis** (criticality: 0.37, depth: 2)
- **run_agent_triage** (criticality: 0.37, depth: 2)
- **suggest_spl** (criticality: 0.37, depth: 2)
- **classify_alert** (criticality: 0.37, depth: 2)
- **route_analysis** (criticality: 0.37, depth: 2)
- *... and 2 more flows.*

## Dependencies

### Outgoing

- `get` (12 edge(s))
- `format` (9 edge(s))
- `str` (8 edge(s))
- `max` (5 edge(s))
- `BaseModel` (5 edge(s))
- `append` (5 edge(s))
- `min` (5 edge(s))
- `raise_for_status` (4 edge(s))
- `json` (4 edge(s))
- `TsocTimeoutError` (4 edge(s))
- `TsocApiError` (4 edge(s))
- `sorted` (4 edge(s))
- `float` (3 edge(s))
- `isinstance` (3 edge(s))
- `model_dump` (3 edge(s))

### Incoming

- `backend/services/alert_classifier_llm.py` (5 edge(s))
- `backend/tests/test_alert_classifier_llm.py` (4 edge(s))
- `backend/services/alert_classifier.py` (3 edge(s))
- `backend/models/agentic_ops.py` (2 edge(s))
- `run` (2 edge(s))
- `backend/tests/test_observability.py` (2 edge(s))
- `backend/devtools/async_client.py` (1 edge(s))
- `backend/devtools/client.py` (1 edge(s))
- `backend/api/routes/analysis.py::run_routed_analysis_endpoint` (1 edge(s))
- `backend/models/agents.py` (1 edge(s))
- `backend/services/agent_triage.py::run_agent_triage` (1 edge(s))
- `backend/services/alert_mcp_enrichment.py::classify_with_optional_mcp` (1 edge(s))
- `backend/api/routes/analysis.py::classify_alert_endpoint` (1 edge(s))
