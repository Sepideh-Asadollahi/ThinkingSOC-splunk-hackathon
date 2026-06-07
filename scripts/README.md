<!-- folder-readme: auto -->
# scripts

Parent: [README.md](../README.md)

Utility scripts for integration setup, testing, and code-graph generation.

## Post-install integration

| Script | Usage |
|--------|--------|
| `configure-integration.sh` | **Full wizard** — Splunk, LiteLLM, MCP, smoke, `.env` summary (`sudo bash scripts/configure-integration.sh`) |
| `configure-integration.sh --smoke` | **Live verification only** (no root required) |
| `setup_splunk_mcp.py` | On Splunk: install/enable **Splunk_MCP_Server** (7931), grant `mcp_tool_execute`, mint token → `backend/.env` |
| `mint_splunk_mcp_token.py` | Mint MCP bearer token only (app already configured on Splunk) |
| `splunk_mcp_lib.py` | Shared REST helpers (imported by setup/mint; do not run directly) |

Related installer smoke entrypoint: `install/smoke-integration-config.sh`

**Documentation:** [docs/23-post-install-integration-wizard.md](../docs/23-post-install-integration-wizard.md)

### Environment variables (Splunk MCP automation)

| Variable | Purpose |
|----------|---------|
| `TSOC_SPLUNK_MCP_APP_PACKAGE` | Local `.spl` / `.tgz` path for `splunk install app` |
| `TSOC_SPLUNK_MCP_APP_URL` | Splunkbase download URL (default: app 7931) |

Example:

```bash
cd /opt/thinking-soc-splunk-hackathon
export TSOC_SPLUNK_MCP_APP_PACKAGE=/path/to/Splunk_MCP_Server.spl
sudo backend/.venv/bin/python scripts/setup_splunk_mcp.py --env backend/.env --splunk-home /opt/splunk
```

## Testing & demo

- `test_splunk_webhook.py` — test Splunk webhook JSON like the frontend (`/analysis/route` or `/alerts/splunk-ingest` + `/storage/events`; see `samples/`). Ingest behavior follows `TSOC_INGEST_AUTO_ANALYZE` in `backend/.env` (no URL query overrides).
- `samples/` — sample Splunk webhook alert payloads for demo and testing

## Setup helpers

- `download-embedding-model.sh` — pre-download FastEmbed ONNX model from `TSOC_EMBEDDING_MODEL` (or pass `bge-small` / `bge-base` / `bge-large`)
- `build-code-graph.sh` — build code-review-graph and export public artifacts under `docs/code-graph/`
