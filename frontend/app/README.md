# frontend/app

Parent: [README.md](../README.md)

Next.js App Router — pages, layouts, and API routes.

## Route groups

| Path | Purpose |
|------|---------|
| `(auth)/login/` | Demo login |
| `(app)/dashboard/` | SOC overview dashboard |
| `(app)/soc-chat/` | SOC analyst chat (RAG) |
| `(app)/analysis/` | Triage queue + stored events |
| `(app)/analysis/investigation/[id]/` | Security investigation detail |
| `(app)/analysis/ops-investigation/[id]/` | Observability investigation detail |
| `(app)/correlation/` | Graph findings list |
| `(app)/correlation/explorer/` | Neo4j graph explorer |
| `(app)/inventory/` | Users & assets CRUD |
| `(app)/relationships/` | User–asset relationship map |
| `(app)/splunk-connection/` | Splunk / LiteLLM / MCP settings |
| `(app)/triage/` | Redirect → `/analysis` (bookmarks) |

## API routes

| Path | Purpose |
|------|---------|
| `api/auth/login/` | Session cookie login |
| `api/auth/logout/` | Clear session |
| `api/backend/[...path]/` | Proxy to FastAPI (`TSOC_BACKEND_URL`) |

## See also

- [README.md](../README.md)
- [16-dashboard.md](../../docs/16-dashboard.md)
