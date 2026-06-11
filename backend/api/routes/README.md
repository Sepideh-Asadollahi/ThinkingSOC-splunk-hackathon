# backend/api/routes

Parent: [README.md](../README.md)

FastAPI route modules mounted under `/api/v1` in `main.py`.

## Contents

| Module | Primary endpoints |
|--------|-------------------|
| `health.py` | `GET /health` |
| `ingest.py` | `POST /api/v1/alerts/splunk-ingest` |
| `analysis.py` | `POST /api/v1/classification/alert`, `/analysis/run`, `/analysis/route`, `/analysis/run-by-sid` |
| `observability.py` | `POST /api/v1/observability/run`, `/observability/run-by-sid` |
| `agents.py` | `POST /api/v1/agents/triage` |
| `triage.py` | `GET /api/v1/triage/queue` |
| `investigation.py` | Investigation timeline and analyst actions |
| `assistant.py` | `POST /api/v1/assistant/spl-suggest` |
| `mcp.py` | `GET /api/v1/mcp/status`, MCP debug tools |
| `llm.py` | `GET /api/v1/llm/status`, `POST /api/v1/llm/chat` |
| `inventory.py` | Inventory CRUD and enrich |
| `storage.py` | `GET /api/v1/storage/events` |
| `soc_chat.py` | `POST /api/v1/soc/chat`, RAG backfill/status |
| `dashboard.py` | `GET /api/v1/dashboard/overview` |
| `integrations.py` | Integration settings for Splunk connection UI |
| `admin_org.py` | `POST /api/v1/admin-org/gap-suggest` |

## See also

- [README.md](../README.md)
- [07-lld-low-level-design.md](../../docs/07-lld-low-level-design.md)
- [05-codebase-map.md](../../docs/05-codebase-map.md)
