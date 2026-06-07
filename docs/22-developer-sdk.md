# Developer SDK & CLI

Typed Python SDK, CLI, and evaluation runner for programmatic access to the ThinkingSOC backend. Designed for integrators, CI pipelines, and demo evidence generation.

**Location:** [`backend/devtools/`](../backend/devtools/)

---

## Overview

| Component | File | Purpose |
|-----------|------|---------|
| Sync client | `client.py` | `TsocSdkClient` — blocking HTTP calls with retry |
| Async client | `async_client.py` | `AsyncTsocSdkClient` — `asyncio`-native variant |
| CLI | `cli.py` | Command-line wrapper for all SDK methods |
| Evaluation runner | `evaluate.py` | Score agent outputs against a scenario matrix |
| Exceptions | `errors.py` | Typed error hierarchy (`TsocAuthError`, `TsocApiError`, …) |
| Examples | `examples/` | Ready-to-use JSON payloads for each endpoint |

### Architecture position

```
                              SDK / CLI (this)
                                   │
                                   ▼
Splunk Alert ──► Webhook ──► FastAPI Backend
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             Splunk REST    Splunk MCP      PostgreSQL
             (v2 jobs)    (SAIA + tools)
```

The SDK wraps the same REST endpoints that the analyst UI uses, with **direct access** to Splunk MCP SAIA, MCP tool invocation, and Splunk REST job analysis. It enables external automation, CI testing, and evidence pack generation without the frontend.

---

## Installation

From the repository root (no separate package install needed):

```bash
cd backend
source .venv/bin/activate
```

Optional — make `devtools` importable from anywhere:

```bash
cd backend/devtools
pip install -e .
```

**Dependencies:** `httpx >= 0.27`, `pydantic >= 2.0` (already in `backend/requirements.txt`).

---

## Authentication

All mutating endpoints accept an optional Bearer token.

```python
client = TsocSdkClient(ingest_token="your-token")
```

Token resolution order:

1. Explicit `ingest_token` parameter
2. `TSOC_INGEST_TOKEN` environment variable
3. No token (requests sent without `Authorization` header)

The token must match the `TSOC_INGEST_TOKEN` configured in `backend/.env`.

---

## SDK API reference

### Constructor parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | `http://127.0.0.1:9876` | Backend base URL |
| `ingest_token` | `str \| None` | `None` | Bearer token (falls back to env) |
| `timeout_seconds` | `float` | `120.0` | Per-request HTTP timeout |
| `max_retries` | `int` | `2` | Retry count for transient failures |
| `retry_backoff_seconds` | `float` | `0.4` | Base backoff between retries (exponential) |

### Methods

#### `classify_alert(body) → AlertClassificationResult`

**Endpoint:** `POST /api/v1/classification/alert`

Classifies an alert into Security or Observability track.

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `normalized` | `dict` | Yes | Alert fields (`host`, `user`, `src`, `cpu`, etc.) |
| `search_name` | `str` | No | Splunk saved search name |
| `sid` | `str` | No | Splunk search job ID |

**Output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `track` | `security \| observability \| unknown` | Detected track (exclusive — not `both`) |
| `recommended_pipeline` | `security \| observability \| manual_review` | Pipeline recommendation (not `dual`) |
| `confidence` | `float` (0–1) | Classification confidence |
| `reason` | `str` | Human-readable reasoning |
| `signals` | `list[str]` | Key signals detected |
| `classification_source` | `rules \| llm \| hybrid` | `llm` when LiteLLM classified; `rules` on manual_review fallback |

**Example:**

```python
from devtools import TsocSdkClient

client = TsocSdkClient(base_url="http://127.0.0.1:9876")
result = client.classify_alert({
    "normalized": {"host": "web-prod-01", "cpu": 95, "latency_ms": 1800},
    "search_name": "Host CPU spike with latency",
})
print(result.track, result.confidence)
# observability 0.92
```

---

#### `route_analysis(body) → AnalysisRouteResponse`

**Endpoint:** `POST /api/v1/analysis/route`

Classifies via LLM (full alert payload), runs **one** analysis pipeline (Security **or** Observability — never both), and returns full results.

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `normalized` | `dict` | Yes | Alert fields |
| `search_name` | `str` | No | Saved search name |
| `sid` | `str` | No | Splunk job ID |
| `row_index` | `int` | No | Which Splunk result row to analyze (default 0) |
| `splunk_results` | `list[dict]` | No | Pre-fetched Splunk job rows |
| `users` | `list[dict]` | No | Inventory user records for enrichment |
| `assets` | `list[dict]` | No | Inventory asset records for enrichment |
| `relationships` | `list[dict]` | No | Entity relationships |

**Key output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `track` | `str` | Resolved track |
| `classification` | `AlertClassificationResult` | Full classification |
| `security_result` | `SocAnalysisResult \| null` | Set when track is `security` |
| `observability_result` | `ObservabilityAnalysisResult \| null` | Set when track is `observability` |
| `mcp_used` | `bool` | Whether Splunk MCP was used |

**Example:**

```python
result = client.route_analysis({
    "search_name": "Suspicious auth failed login alert",
    "normalized": {"host": "web-prod-01", "user": "jdoe", "src": "1.2.3.4"},
    "users": [{"user_id": "jdoe", "risk_score": "3", "department": "IT"}],
    "assets": [{"asset_id": "srv-web-01", "hostname": "web-prod-01", "criticality": "high"}],
})
print(result.track, result.mcp_used)
```

---

#### `run_agent_triage(body) → AgentTriageResponse`

**Endpoint:** `POST /api/v1/agents/triage`

Full agentic triage: classify → analyze → triage score → SPL suggestion → next actions.

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `normalized` | `dict` | Yes | Alert fields |
| `search_name` | `str` | No | Saved search name |
| `sid` | `str` | No | Splunk job ID |
| `operator_goal` | `str` | No | Analyst intent (e.g. "confirm lateral movement") |
| `users` | `list[dict]` | No | Inventory users |
| `assets` | `list[dict]` | No | Inventory assets |
| `relationships` | `list[dict]` | No | Entity relationships |

**Key output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `track` | `str` | Resolved track |
| `classification` | `AlertClassificationResult` | Classification details |
| `agent_summary` | `str` | Human-readable triage summary |
| `next_actions` | `list[str]` | Recommended operator actions |
| `security_result` | `SocAnalysisResult \| null` | Security pipeline output |
| `observability_result` | `ObservabilityAnalysisResult \| null` | Observability pipeline output |
| `suggested_spl` | `SplAssistantSuggestResponse \| null` | Investigation SPL |
| `mcp_used` | `bool` | Whether Splunk MCP was used |
| `security_triage` | `TriageOutcome \| null` | Triage priority score (security) |
| `observability_triage` | `TriageOutcome \| null` | Triage priority score (observability) |

**Example:**

```python
result = client.run_agent_triage({
    "search_name": "Suspicious auth failed login alert",
    "operator_goal": "confirm lateral movement path",
    "normalized": {"host": "web-prod-01", "user": "jdoe", "src": "1.2.3.4"},
    "users": [{"user_id": "jdoe", "risk_score": "3"}],
    "assets": [{"asset_id": "srv-web-01", "hostname": "web-prod-01", "criticality": "high"}],
})
print(result.agent_summary)
print(result.next_actions)
```

---

#### `suggest_spl(body) → SplAssistantSuggestResponse`

**Endpoint:** `POST /api/v1/assistant/spl-suggest`

Generates analyst-ready SPL for the next investigation step. Uses SAIA REST `/predict` with optional MCP execute, falling back to LiteLLM or rule-based generation.

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `normalized` | `dict` | Yes | Alert fields |
| `search_name` | `str` | No | Saved search name |
| `sid` | `str` | No | Splunk job ID |
| `objective` | `str` | No | Analyst intent (e.g. "collect root cause timeline") |

**Output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `source` | `str` | Generation method (`llm`, `rule_based`, `rest_predict`, `rest_predict_execute`, …) |
| `root_cause_spl` | `RootCauseSpl` | Generated SPL with metadata |
| `spl_results` | `SplSearchResult \| null` | MCP execute results (when available) |

**Example:**

```python
result = client.suggest_spl({
    "normalized": {"host": "web-prod-01", "user": "jdoe", "src": "1.2.3.4"},
    "search_name": "Suspicious auth activity",
    "objective": "collect root cause timeline",
})
print(result.source)              # "rest_predict" or "rule_based"
print(result.root_cause_spl.spl)  # "search index=... | ..."
```

---

#### `mcp_status() → dict`

**Endpoint:** `GET /api/v1/mcp/status`

Checks Splunk MCP Server connectivity. Does not require an ingest token.

**Output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `configured` | `bool` | MCP settings present in config |
| `connected` | `bool` | MCP server reachable |
| `url` | `str \| null` | MCP server URL |
| `server_info` | `dict` | Server metadata (version, name, etc.) |
| `tools` | `list[str]` | Available MCP tool names |
| `saia_available` | `bool` | SAIA `/predict` available |
| `message` | `str \| null` | Status message or error detail |

**Example:**

```python
status = client.mcp_status()
print(status["configured"], status["connected"])
print(status["tools"])           # ["splunk_run_query", "splunk_get_indexes", ...]
print(status["saia_available"])  # True
```

---

#### `mcp_generate_spl(body) → McpSplGenerateResponse`

**Endpoint:** `POST /api/v1/mcp/spl-generate`

Generates SPL from a natural-language description using Splunk MCP Server SAIA (generate + optimize + explain pipeline).

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | `str` | Yes | Natural-language description of the desired search |
| `index` | `str` | No | Target Splunk index |
| `context` | `str` | No | Additional alert/search context for the Assistant |

**Output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `source` | `splunk_mcp_saia \| unavailable` | Whether SAIA generated the SPL |
| `spl` | `str \| null` | Generated SPL query |
| `explanation` | `str \| null` | Natural-language explanation of the SPL |

**Example:**

```python
result = client.mcp_generate_spl({
    "query": "Show failed login attempts for user jdoe in the last 24 hours",
    "index": "main",
})
print(result.source)       # "splunk_mcp_saia"
print(result.spl)          # "search index=main action=failure user=jdoe ..."
print(result.explanation)  # "This search finds all failed ..."
```

---

#### `mcp_call_tool(body) → McpToolCallResponse`

**Endpoint:** `POST /api/v1/mcp/tools/call`

Invokes any Splunk MCP Server tool by name. Available tools: `splunk_run_query`, `splunk_get_indexes`, `splunk_get_metadata`, `splunk_get_info`, `saia_generate_spl`, `saia_optimize_spl`, `saia_explain_spl`, `saia_ask_splunk_question`.

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool_name` | `str` | Yes | MCP tool name |
| `arguments` | `dict` | No | Tool-specific arguments |

**Output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `str` | Echoed tool name |
| `result` | `any` | Tool-specific result (rows, metadata, etc.) |

**Example:**

```python
# Run a Splunk query via MCP
result = client.mcp_call_tool({
    "tool_name": "splunk_run_query",
    "arguments": {"search_query": "search index=main host=web-prod-01 | stats count by user"},
})
print(result.result)

# List available indexes
indexes = client.mcp_call_tool({"tool_name": "splunk_get_indexes"})
print(indexes.result)
```

---

#### `run_analysis(body) → SocAnalysisResult`

**Endpoint:** `POST /api/v1/analysis/run`

Runs the SOC security analysis pipeline directly (Defender + Hunter + Judge) without routing. Accepts an `AnalysisRunRequest` or dict.

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `normalized` | `dict` | Yes | Alert fields (`host`, `user`, `src`, etc.) |
| `search_name` | `str` | No | Splunk saved search name |
| `sid` | `str` | No | Splunk search job ID |
| `row_index` | `int` | No | Splunk result row (default 0) |
| `splunk_results` | `list[dict]` | No | Pre-fetched Splunk job rows |
| `enrichment` | `EnrichmentResult` | No | Pre-computed enrichment |
| `users` | `list[dict]` | No | Inventory users (inline) |
| `assets` | `list[dict]` | No | Inventory assets (inline) |

**Key output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `defender` | `str` | Defender assessment narrative |
| `hunter` | `HunterSection` | Threat hunting findings |
| `judge` | `JudgeVerdict` | Final verdict with confidence |
| `investigation_questions` | `list[InvestigationQuestionItem]` | Follow-up questions with SPL |
| `enrichment` | `EnrichmentResult` | Asset identity enrichment |

**Example:**

```python
result = client.run_analysis({
    "normalized": {"host": "web-prod-01", "user": "jdoe", "src": "1.2.3.4"},
    "search_name": "Suspicious auth failed login",
})
print(result.judge.verdict, result.judge.confidence)
```

---

#### `run_analysis_by_sid(body) → AnalysisBatchBySidResponse`

**Endpoint:** `POST /api/v1/analysis/run-by-sid`

Fetches all Splunk job results for a given SID via Splunk REST API v2, then runs SOC analysis on each result row. Direct demonstration of Splunk REST integration.

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sid` | `str` | Yes | Splunk search job ID |
| `search_name` | `str` | No | Saved search name |
| `normalized` | `dict` | No | Base fields merged with each row |
| `users` | `list[dict]` | No | Inventory users |
| `assets` | `list[dict]` | No | Inventory assets |

**Key output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `sid` | `str` | Echoed job ID |
| `splunk_results_row_count` | `int` | Total rows from Splunk REST |
| `analyzed_row_count` | `int` | Rows analyzed |
| `rows` | `list[RowAnalysisOutcome]` | Per-row analysis results |

**Example:**

```python
result = client.run_analysis_by_sid({
    "sid": "1716800000.12345",
    "search_name": "Suspicious auth failed login alert",
    "users": [{"user_id": "jdoe", "risk_score": "3"}],
})
print(f"Analyzed {result.analyzed_row_count} of {result.splunk_results_row_count} rows")
for row in result.rows:
    print(row.row_index, row.track, row.classification.confidence)
```

---

#### `search_events(...) → dict`

**Endpoint:** `GET /api/v1/storage/events`

Queries stored analysis records from PostgreSQL.

**Parameters (all optional keyword args):**

| Parameter | Type | Description |
|-----------|------|-------------|
| `sid` | `str` | Filter by Splunk job ID |
| `record_type` | `str` | Filter by record type (`soc_analysis`, `observability_analysis`, etc.) |
| `row_index` | `int` | Filter by row index |
| `limit` | `int` | Max results |

**Example:**

```python
result = client.search_events(record_type="soc_analysis", limit=5)
print(f"Found {result['count']} records")
for r in result["results"]:
    print(r["id"], r["tsoc_record_type"])
```

---

#### `get_event(record_id) → dict`

**Endpoint:** `GET /api/v1/storage/events/{record_id}`

Fetches a single stored record by PostgreSQL primary key.

| Parameter | Type | Description |
|-----------|------|-------------|
| `record_id` | `int` | PostgreSQL row ID |

```python
event = client.get_event(42)
print(event["tsoc_record_type"], event["payload"])
```

---

#### `dashboard_overview() → DashboardOverview`

**Endpoint:** `GET /api/v1/dashboard/overview`

Returns SOC dashboard KPIs, triage statistics, activity timeline, and integration status.

**Key output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `kpis.total_records` | `int` | Total stored records |
| `kpis.analyses_24h` | `int` | Analyses in last 24 hours |
| `kpis.health_score` | `float` | System health score |
| `track_split` | `TrackSplit` | Count by security / observability (legacy `both` may appear in old data) |
| `integrations` | `DashboardIntegrations` | Splunk/MCP/Postgres config status |

**Example:**

```python
overview = client.dashboard_overview()
print(f"Health: {overview.kpis.health_score}%")
print(f"Splunk configured: {overview.integrations.splunk_configured}")
print(f"MCP configured: {overview.integrations.mcp_configured}")
```

---

#### `run_observability(body) → ObservabilityAnalysisResult`

**Endpoint:** `POST /api/v1/observability/run`

Runs the Observability analysis pipeline (Diagnoser + Responder + OpsJudge) without routing.

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `normalized` | `dict` | Yes | Alert fields (`host`, `service`, `cpu`, `latency_ms`, etc.) |
| `search_name` | `str` | No | Splunk saved search name |
| `sid` | `str` | No | Splunk search job ID |
| `row_index` | `int` | No | Splunk result row (default 0) |
| `splunk_results` | `list[dict]` | No | Pre-fetched Splunk job rows |
| `users` | `list[dict]` | No | Inventory users |
| `assets` | `list[dict]` | No | Inventory assets |

**Key output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `diagnoser` | `DiagnoserSection` | Root cause hypotheses + follow-up searches |
| `responder` | `ResponderSection` | Recommended actions + safety notes |
| `ops_judge` | `OpsJudgeVerdict` | Final verdict, priority, confidence, rationale |
| `entity_resolution` | `EntityResolution` | Host/service/asset resolution |
| `impact_context` | `ImpactContext` | Business impact assessment |

**Example:**

```python
result = client.run_observability({
    "normalized": {"host": "web-prod-01", "cpu": 95, "latency_ms": 1800},
    "search_name": "Host CPU spike with latency",
})
print(result.ops_judge.verdict, result.ops_judge.priority)
```

---

#### `run_observability_by_sid(body) → ObservabilityBatchBySidResponse`

**Endpoint:** `POST /api/v1/observability/run-by-sid`

Fetches Splunk job results by SID via REST API v2, then runs Observability analysis on each row. Mirrors `run_analysis_by_sid` for the Observability pipeline.

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sid` | `str` | Yes | Splunk search job ID |
| `search_name` | `str` | No | Saved search name |
| `normalized` | `dict` | No | Base fields merged with each row |
| `users` | `list[dict]` | No | Inventory users |
| `assets` | `list[dict]` | No | Inventory assets |
| `max_rows` | `int` | No | Max rows to analyze (default 100) |

**Example:**

```python
result = client.run_observability_by_sid({
    "sid": "1716800000.12345",
    "search_name": "Host CPU spike",
})
print(f"Analyzed {result.analyzed_row_count} observability rows")
```

---

#### `soc_chat(body) → SocChatResponse`

**Endpoint:** `POST /api/v1/soc/chat`

AI-powered investigation chat grounded in indexed Splunk alert and analysis data. Uses RAG (Retrieval-Augmented Generation) with PostgreSQL or Qdrant vector search for context.

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messages` | `list[SocChatMessage]` | Yes | Chat messages (`role` + `content`) |
| `filters` | `SocChatFilters` | No | Filter by SID, record type, etc. |
| `conversation_id` | `str` | No | Continue an existing conversation |

**Key output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `answer` | `str` | AI-generated answer grounded in analysis data |
| `citations` | `list[SocChatCitation]` | Source records cited in the answer |
| `splunk_mcp_used` | `bool` | Whether MCP was used for live data |
| `retrieval_backend` | `str` | `postgres` or `qdrant` |
| `conversation_id` | `str \| null` | Conversation ID for follow-ups |

**Example:**

```python
result = client.soc_chat({
    "messages": [
        {"role": "user", "content": "What are the most critical security findings today?"},
    ],
})
print(result.answer)
print(f"Citations: {len(result.citations)}, Backend: {result.retrieval_backend}")
```

---

#### `soc_chat_status() → dict`

**Endpoint:** `GET /api/v1/soc/chat/status`

RAG backend status: Postgres, Qdrant vector store, document count, active embedding model (`embedding_model`, `embedding_dim`).

```python
status = client.soc_chat_status()
print(status["enabled"], status["document_count"])
print(status["default_retrieval"])  # "qdrant" or "postgres"
print(status.get("embedding_model"), status.get("embedding_dim"))
```

---

#### `investigation_timeline(record_id) → dict`

**Endpoint:** `GET /api/v1/investigation/records/{record_id}/timeline`

Chronological investigation steps for an alert tied to a stored record. Traces the full lifecycle: ingest → classification → enrichment → analysis → triage.

| Parameter | Type | Description |
|-----------|------|-------------|
| `record_id` | `int` | PostgreSQL record ID |

```python
timeline = client.investigation_timeline(42)
for step in timeline["steps"]:
    print(step["phase"], step.get("timestamp"))
```

---

#### `analyst_actions(record_id) → dict`

**Endpoint:** `GET /api/v1/investigation/records/{record_id}/analyst-actions`

Retrieves human-in-the-loop action log (acknowledge/escalate) for a record.

```python
actions = client.analyst_actions(42)
for a in actions["results"]:
    print(a["action"], a.get("analyst"), a.get("note"))
```

---

#### `add_analyst_action(record_id, body) → dict`

**Endpoint:** `POST /api/v1/investigation/records/{record_id}/analyst-actions`

Records an analyst acknowledge or escalate decision (human gate in the agentic workflow).

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | `acknowledge \| escalate` | Yes | Analyst decision |
| `note` | `str` | No | Analyst note (max 2000 chars) |
| `analyst` | `str` | No | Analyst identifier |

```python
result = client.add_analyst_action(42, {
    "action": "escalate",
    "note": "Confirmed lateral movement, escalating to IR",
    "analyst": "analyst-01",
})
print(result["saved"])
```

---

#### `triage_queue(...) → dict`

**Endpoint:** `GET /api/v1/triage/queue`

Priority-sorted analyst review queue. Returns stored analyses ranked by triage score (highest first).

**Parameters (keyword args):**

| Parameter | Type | Description |
|-----------|------|-------------|
| `track` | `all \| security \| observability` | Filter by pipeline track |
| `limit` | `int` | Max results (default 50) |

```python
queue = client.triage_queue(track="security", limit=10)
print(f"{queue['count']} items in queue")
for item in queue["results"]:
    print(item.get("triage_score"), item.get("verdict"))
```

---

#### `health() → dict`

**Endpoint:** `GET /api/v1/health`

Backend liveness check.

```python
assert client.health()["status"] == "ok"
```

---

## Async client

`AsyncTsocSdkClient` provides the same methods as `TsocSdkClient`, but `async`. Constructor parameters are identical.

```python
import asyncio
from devtools import AsyncTsocSdkClient

async def main():
    client = AsyncTsocSdkClient(base_url="http://127.0.0.1:9876")
    result = await client.classify_alert({"normalized": {"cpu": 95}})
    print(result.track)
    status = await client.mcp_status()
    print(status["connected"])

asyncio.run(main())
```

---

## CLI

All SDK methods are available from the command line.

### Global options

```bash
python backend/devtools/cli.py --help
```

| Flag | Default | Description |
|------|---------|-------------|
| `--base-url` | `http://127.0.0.1:9876` | Backend URL |
| `--token` | `TSOC_INGEST_TOKEN` env | Bearer token |
| `--timeout` | `120.0` | HTTP timeout (seconds) |
| `--retries` | `2` | Retry count |

### Commands

```bash
# Classify an alert
python backend/devtools/cli.py classify --body backend/devtools/examples/classify.json

# Route analysis (classify + full pipeline)
python backend/devtools/cli.py route --body backend/devtools/examples/route.json

# Agent triage (full agentic flow)
python backend/devtools/cli.py agent --body backend/devtools/examples/agent.json

# SPL suggestion
python backend/devtools/cli.py spl --body backend/devtools/examples/spl.json

# MCP status check (no body needed)
python backend/devtools/cli.py mcp-status

# Generate SPL via Splunk MCP SAIA (NL → SPL)
python backend/devtools/cli.py mcp-generate --body backend/devtools/examples/mcp_generate.json

# Invoke any Splunk MCP tool directly
python backend/devtools/cli.py mcp-tool --body backend/devtools/examples/mcp_tool_call.json

# Batch analysis by Splunk SID (REST v2 job results)
python backend/devtools/cli.py run-by-sid --body backend/devtools/examples/run_by_sid.json

# Observability analysis (Diagnoser + Responder + OpsJudge)
python backend/devtools/cli.py obs-run --body backend/devtools/examples/classify.json

# Observability batch by SID
python backend/devtools/cli.py obs-by-sid --body backend/devtools/examples/run_by_sid.json

# SOC Chat (RAG investigation)
python backend/devtools/cli.py soc-chat --body backend/devtools/examples/soc_chat.json

# SOC Chat status
python backend/devtools/cli.py chat-status

# Investigation timeline
python backend/devtools/cli.py timeline --record-id 42

# Triage queue
python backend/devtools/cli.py triage --track security --limit 10

# SOC dashboard overview
python backend/devtools/cli.py dashboard

# Health check
python backend/devtools/cli.py health
```

All commands output JSON to stdout.

---

## Evaluation runner

Runs predefined scenarios against the backend and produces an objective quality report. Useful for demo evidence and regression testing.

```bash
python backend/devtools/evaluate.py \
  --matrix backend/devtools/examples/eval_matrix.json \
  --out eval_report.json
```

### Scoring rubric (per scenario, 100 points max)

| Check | Points | Condition |
|-------|--------|-----------|
| Track routing | 30 | `track` matches `expected_track` |
| Confidence | 15 | `confidence >= 0.6` |
| Next actions | 15 | At least 3 actions returned |
| Pipeline output | 20 | Expected pipeline result present |
| SPL quality | 20 | Contains `search` keyword, length >= 30 chars |

### Report output

```json
{
  "scenario_count": 2,
  "max_score": 200,
  "total_score": 180,
  "score_percent": 90.0,
  "results": [
    {
      "scenario_index": 0,
      "scenario_name": "security_failed_login",
      "score": 100,
      "details": { "track_match": true, "confidence_ok": true, ... }
    }
  ]
}
```

---

## Exception hierarchy

All exceptions inherit from `TsocSdkError`:

| Exception | HTTP codes | Behavior |
|-----------|------------|----------|
| `TsocAuthError` | 401, 403 | Raised immediately (no retry) |
| `TsocNotFoundError` | 404 | Raised immediately (no retry) |
| `TsocTimeoutError` | — | After all retries exhausted |
| `TsocApiError` | 500+ | Retried up to `max_retries`, then raised |

Transient failures (500, 502, 503, 504, timeout) are retried with exponential backoff.

---

## Example payloads

Ready-to-use JSON files in [`backend/devtools/examples/`](../backend/devtools/examples/):

| File | Endpoint | Scenario |
|------|----------|----------|
| `classify.json` | `/classification/alert` | Observability — CPU spike + latency on `web-prod-01` |
| `route.json` | `/analysis/route` | Security — failed login with user/asset enrichment + identity rules |
| `agent.json` | `/agents/triage` | Security — full triage with operator goal "confirm lateral movement" |
| `spl.json` | `/assistant/spl-suggest` | Security — root cause timeline for auth activity |
| `mcp_generate.json` | `/mcp/spl-generate` | SAIA NL→SPL — "Show failed login attempts for user jdoe" |
| `mcp_tool_call.json` | `/mcp/tools/call` | Raw MCP — run `splunk_run_query` with stats aggregation |
| `run_by_sid.json` | `/analysis/run-by-sid` | Splunk REST — batch-analyze job results by SID |
| `soc_chat.json` | `/soc/chat` | RAG chat — ask about recent security findings |
| `eval_matrix.json` | `evaluate.py` | 2-scenario matrix (security + observability) with scoring expectations |
| `demo_e2e.py` | End-to-end | Full pipeline demo: health → classify → triage → SPL → MCP → chat |

---

## Splunk integration context

The SDK provides **direct programmatic access** to Splunk capabilities:

| Splunk capability | SDK method | Integration path |
|-------------------|------------|-----------------|
| **Splunk REST API v2** (job results) | `run_analysis_by_sid()`, `run_observability_by_sid()` | Backend fetches results via `GET /services/search/v2/jobs/{sid}/results` |
| **Splunk MCP Server** (tool execution) | `mcp_call_tool()` | JSON-RPC `tools/call` to any registered MCP tool (`splunk_run_query`, `get_indexes`, etc.) |
| **Splunk MCP SAIA** (NL → SPL) | `mcp_generate_spl()` | `saia_generate_spl` + optimize + explain pipeline |
| **SAIA REST `/predict`** | `suggest_spl()` | `POST /servicesNS/.../predict` with MCP execute fallback |
| **Splunk MCP status** | `mcp_status()` | Connectivity + tool inventory + SAIA availability |
| **RAG over Splunk data** | `soc_chat()` | AI investigation chat grounded in indexed Splunk alerts and analyses |
| **Investigation lifecycle** | `investigation_timeline()`, `analyst_actions()`, `add_analyst_action()` | Chronological tracing + human-in-the-loop gate |
| **Triage prioritization** | `triage_queue()` | Priority-sorted analyst queue from analyzed Splunk alerts |
| **Dual pipeline** | `run_analysis()` + `run_observability()` | Security and Observability parallel pipelines |
| **Webhook alert action** | Separate ingest endpoint | SDK wraps downstream analysis triggered by alerts |

This makes the SDK a **complete programmatic interface** to the ThinkingSOC platform, demonstrating **Splunk Developer Tools** usage across REST API v2 data retrieval, MCP Server tool invocation, SAIA AI-assisted SPL generation, RAG-powered investigation, and the full alert-to-triage lifecycle.

---

## Related documents

- [04-agents-and-pipelines.md](./04-agents-and-pipelines.md) — Agent pipeline details
- [06-hld-high-level-design.md](./06-hld-high-level-design.md) — High-level design
- [13-cim-investigation-spl-mcp.md](./13-cim-investigation-spl-mcp.md) — SPL generation and MCP execution
- [15-splunk-mcp-integration.md](./15-splunk-mcp-integration.md) — Splunk MCP Server integration
- [backend/devtools/README.md](../backend/devtools/README.md) — SDK quickstart
