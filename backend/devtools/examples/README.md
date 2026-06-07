# backend/devtools/examples

Parent: [README.md](../README.md) | Full reference: [docs/22-developer-sdk.md](../../../docs/22-developer-sdk.md)

Ready-to-use JSON payloads for the SDK CLI and evaluation runner.

## Payloads

| File | CLI command | Endpoint | Scenario |
|------|-------------|----------|----------|
| `classify.json` | `cli.py classify` | `POST /api/v1/classification/alert` | Observability — CPU spike (95%) + latency (1800 ms) on `web-prod-01` / `payment-api` |
| `route.json` | `cli.py route` | `POST /api/v1/analysis/route` | Security — failed login for `jdoe` from `1.2.3.4`, with user/asset inventory and identity rules |
| `agent.json` | `cli.py agent` | `POST /api/v1/agents/triage` | Security — same failed login with `operator_goal: "confirm lateral movement path"` |
| `spl.json` | `cli.py spl` | `POST /api/v1/assistant/spl-suggest` | Security — generate root cause timeline SPL for auth activity on `web-prod-01` |
| `mcp_generate.json` | `cli.py mcp-generate` | `POST /api/v1/mcp/spl-generate` | Splunk MCP SAIA — NL→SPL "Show failed login attempts for user jdoe in the last 24 hours" |
| `mcp_tool_call.json` | `cli.py mcp-tool` | `POST /api/v1/mcp/tools/call` | Splunk MCP — run `splunk_run_query` with stats aggregation on `web-prod-01` |
| `run_by_sid.json` | `cli.py run-by-sid` | `POST /api/v1/analysis/run-by-sid` | Splunk REST v2 — batch-analyze job results by SID with user/asset enrichment |
| `soc_chat.json` | `cli.py soc-chat` | `POST /api/v1/soc/chat` | RAG chat — ask about recent critical security findings |
| `eval_matrix.json` | `evaluate.py --matrix` | Multiple | 2-scenario matrix: one security (failed login) + one observability (CPU spike), with expected tracks |
| `demo_e2e.py` | `python demo_e2e.py` | End-to-end | Full pipeline demo script: health → classify → triage → SPL → MCP → chat |

## Usage

```bash
# Single endpoint call
python backend/devtools/cli.py classify --body backend/devtools/examples/classify.json

# Splunk MCP SAIA (NL → SPL)
python backend/devtools/cli.py mcp-generate --body backend/devtools/examples/mcp_generate.json

# Raw Splunk MCP tool call
python backend/devtools/cli.py mcp-tool --body backend/devtools/examples/mcp_tool_call.json

# Batch analysis by Splunk SID
python backend/devtools/cli.py run-by-sid --body backend/devtools/examples/run_by_sid.json

# SOC Chat (RAG investigation)
python backend/devtools/cli.py soc-chat --body backend/devtools/examples/soc_chat.json

# End-to-end demo (requires running backend)
python backend/devtools/examples/demo_e2e.py

# Full evaluation (requires running backend)
python backend/devtools/evaluate.py \
  --matrix backend/devtools/examples/eval_matrix.json \
  --out eval_report.json
```

## Adding scenarios

To add a scenario to the evaluation matrix, append an object to `scenarios` in `eval_matrix.json`:

```json
{
  "name": "your_scenario_name",
  "expected_track": "security",
  "search_name": "Your Splunk saved search name",
  "operator_goal": "what the analyst wants to confirm",
  "normalized": { "host": "...", "user": "..." },
  "users": [],
  "assets": []
}
```

## See also

- [backend/devtools/README.md](../README.md) — SDK quickstart
- [docs/22-developer-sdk.md](../../../docs/22-developer-sdk.md) — Full API reference and evaluation rubric
