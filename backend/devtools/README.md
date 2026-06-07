# ThinkingSOC Developer SDK

This folder provides a typed Python SDK and CLI for calling backend endpoints used in the hackathon demo.

## What is included

- `TsocSdkClient` (sync)
- `AsyncTsocSdkClient` (async)
- Standard exception types:
  - `TsocAuthError`
  - `TsocNotFoundError`
  - `TsocTimeoutError`
  - `TsocApiError`
- CLI: `backend/devtools/cli.py`
- Evaluation runner: `backend/devtools/evaluate.py`

## Supported APIs

**Analysis & triage:**
- `POST /api/v1/classification/alert` — LLM classification (full alert payload → `security` | `observability` | `manual_review`)
- `POST /api/v1/analysis/route` — classify + run **one** pipeline (Security **or** Observability, never both)
- `POST /api/v1/analysis/run` — run SOC analysis directly
- `POST /api/v1/analysis/run-by-sid` — batch-analyze Splunk job results by SID (Splunk REST v2)
- `POST /api/v1/observability/run` — run Observability pipeline (Diagnoser + Responder + OpsJudge)
- `POST /api/v1/observability/run-by-sid` — batch observability analysis by SID
- `POST /api/v1/agents/triage` — full agentic triage flow
- `POST /api/v1/assistant/spl-suggest` — generate investigation SPL

**Splunk MCP integration:**
- `GET /api/v1/mcp/status` — MCP connectivity + SAIA availability
- `POST /api/v1/mcp/spl-generate` — NL→SPL via Splunk MCP SAIA
- `POST /api/v1/mcp/tools/call` — invoke any Splunk MCP tool directly

**SOC Chat (RAG):**
- `POST /api/v1/soc/chat` — AI investigation chat grounded in Splunk data
- `GET /api/v1/soc/chat/status` — RAG backend status

**Investigation & triage:**
- `GET /api/v1/investigation/records/{id}/timeline` — investigation timeline
- `GET /api/v1/investigation/records/{id}/analyst-actions` — analyst action log
- `POST /api/v1/investigation/records/{id}/analyst-actions` — record acknowledge/escalate
- `GET /api/v1/triage/queue` — priority-sorted analyst queue

**Storage & dashboard:**
- `GET /api/v1/storage/events` — query stored records
- `GET /api/v1/storage/events/{id}` — fetch single record
- `GET /api/v1/dashboard/overview` — SOC dashboard KPIs
- `GET /api/v1/health` — backend liveness

Full API reference: [docs/22-developer-sdk.md](../../docs/22-developer-sdk.md)

## Quickstart (sync)

```python
from devtools import TsocSdkClient

client = TsocSdkClient(
    base_url="http://127.0.0.1:9876",
    ingest_token="your-token",
    timeout_seconds=90,
    max_retries=2,
)

res = client.classify_alert(
    {
        "normalized": {"host": "web-prod-01", "cpu": 95, "latency_ms": 1800},
        "search_name": "Host CPU spike with latency",
    }
)
print(res.track, res.recommended_pipeline)

status = client.mcp_status()
print(status.get("connected"), status.get("saia_available"))
```

## Quickstart (Splunk MCP)

```python
# Generate SPL from natural language via Splunk MCP SAIA
spl = client.mcp_generate_spl({
    "query": "Show failed login attempts for user jdoe in the last 24 hours",
    "index": "main",
})
print(spl.source, spl.spl)

# Run any Splunk MCP tool
result = client.mcp_call_tool({
    "tool_name": "splunk_run_query",
    "arguments": {"search_query": "search index=main | stats count by host"},
})
print(result.result)

# Batch-analyze a Splunk job by SID (fetches via REST v2)
batch = client.run_analysis_by_sid({"sid": "1716800000.12345"})
print(f"Analyzed {batch.analyzed_row_count} rows from Splunk")
```

## Quickstart (async)

```python
import asyncio
from devtools import AsyncTsocSdkClient

async def main():
    client = AsyncTsocSdkClient(base_url="http://127.0.0.1:9876", ingest_token="your-token")
    res = await client.suggest_spl(
        {
            "normalized": {"host": "web-prod-01", "user": "jdoe", "src": "1.2.3.4"},
            "objective": "collect root cause timeline",
        }
    )
    print(res.source, res.root_cause_spl.spl)

asyncio.run(main())
```

## CLI

```bash
python backend/devtools/cli.py --help
python backend/devtools/cli.py classify --body backend/devtools/examples/classify.json
python backend/devtools/cli.py route --body backend/devtools/examples/route.json
python backend/devtools/cli.py agent --body backend/devtools/examples/agent.json
python backend/devtools/cli.py spl --body backend/devtools/examples/spl.json
python backend/devtools/cli.py mcp-status
python backend/devtools/cli.py mcp-generate --body backend/devtools/examples/mcp_generate.json
python backend/devtools/cli.py mcp-tool --body backend/devtools/examples/mcp_tool_call.json
python backend/devtools/cli.py run-by-sid --body backend/devtools/examples/run_by_sid.json
python backend/devtools/cli.py obs-run --body backend/devtools/examples/classify.json
python backend/devtools/cli.py obs-by-sid --body backend/devtools/examples/run_by_sid.json
python backend/devtools/cli.py soc-chat --body backend/devtools/examples/soc_chat.json
python backend/devtools/cli.py chat-status
python backend/devtools/cli.py timeline --record-id 42
python backend/devtools/cli.py triage --track security --limit 10
python backend/devtools/cli.py dashboard
python backend/devtools/cli.py health
```

Token fallback order:

1. `--token`
2. `TSOC_INGEST_TOKEN` environment variable

## Notes

- SDK methods return typed Pydantic models from backend contracts.
- Retries apply only to transient failures (`500`, `502`, `503`, `504`, and timeouts).
- For auth failures (`401`, `403`), SDK raises `TsocAuthError` immediately.

## Optional packaging

From `backend/devtools/`:

```bash
pip install -e .
```

This exposes the `devtools` and `models` packages in your Python environment.

## Evaluation rubric runner (for demo evidence)

Use predefined scenarios to produce an objective score report:

```bash
python backend/devtools/evaluate.py \
  --matrix backend/devtools/examples/eval_matrix.json \
  --out backend/devtools/examples/eval_report.json
```

The report includes:

- Track routing correctness
- Confidence threshold checks
- Presence of actionable next steps
- Presence of pipeline outputs
- SPL suggestion quality checks

