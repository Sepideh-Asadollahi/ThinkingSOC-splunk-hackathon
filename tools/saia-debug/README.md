# SAIA / MCP debug probe (standalone)

Small tool **outside ThinkingSOC Lite** to compare Splunk AI Assistant paths (UI `/predict` vs MCP `generatespl`).

**ThinkingSOC Lite production SPL** uses REST **`/predict`** + MCP **`splunk_run_query`** — see [docs/13-cim-investigation-spl-mcp.md](../../docs/13-cim-investigation-spl-mcp.md).

## Common cause (summary)

| Path | Splunk endpoint | Typical |
|------|-----------------|---------|
| **UI chat / ThinkingSOC Lite** | `POST .../Splunk_AI_Assistant_Cloud/predict` | Works |
| **MCP generatespl** | `POST .../Splunk_AI_Assistant_Cloud/generatespl` | May **404** on some tenants (v2 vs v1) |

If MCP `saia_generate_spl` fails but UI chat works, use `/predict` (as the backend does) or inspect `base_rest.py` on the Splunk host manually.

**ThinkingSOC Lite backend** auto-repairs SAIA `cloud_connected_configurations` when KV/conf is incomplete (`TSOC_SAIA_AUTO_REPAIR=true`, default). See [docs/13-cim-investigation-spl-mcp.md](../../docs/13-cim-investigation-spl-mcp.md#saia-cloud-config-auto-repair).

## Run

```bash
cd /opt/thinking-soc-splunk-hackathon/tools/saia-debug
pip install httpx   # or use backend/.venv
export SPLUNK_MGMT_URL=https://127.0.0.1:8089
export SPLUNK_USERNAME=admin
export SPLUNK_PASSWORD='...'
export SPLUNK_VERIFY_SSL=false
export SPLUNK_MCP_TOKEN='...'   # optional

python debug_saia_paths.py
```

Or with backend `.env`:

```bash
python debug_saia_paths.py --env /opt/thinking-soc-splunk-hackathon/backend/.env
```

## Output

Per probe: `PASS` / `FAIL` / `SKIP` + URL + response summary.

Final **Diagnosis** section explains UI v1 vs MCP v2 — not a ThinkingSOC Lite application bug.
