# graph_api

FastAPI routers exposing the Graph Correlation REST API. All endpoints live under `/api/v1/graph/` and require bearer-token or demo-API-key authentication.

## Key files

| File | Description |
|------|-------------|
| `analysis_router.py` | `POST /analysis/discover-attack-paths` (async) and operation status polling |
| `explorer_router.py` | `GET /topology/{id}` and `GET /attack-tree/{id}` graph exploration endpoints |
| `findings_router.py` | CRUD for graph findings — list, get, get graph-data, patch ticket |
| `internal_router.py` | `POST /internal/correlate` — internal correlation endpoint (demo-API-key auth) |
| `deps.py` | FastAPI dependency helpers for bearer-token and demo-API-key validation |

## Related docs

- [Correlation Graph Service](../../docs/12-correlation-graph-service.md)
