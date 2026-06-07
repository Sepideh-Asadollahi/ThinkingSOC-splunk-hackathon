# Graph Correlation — integrated into unified backend

Correlation API is mounted on the **main hackathon backend** at `/api/v1/graph`.

**Full documentation:** [docs/12-correlation-graph-service.md](../docs/12-correlation-graph-service.md)

## Run (single process)

```bash
cd backend
docker compose up -d postgres neo4j
python run.py
```

Default URL: **http://127.0.0.1:9876/api/v1/graph** (same port as `TSOC_HTTP_PORT`).

OpenAPI: http://127.0.0.1:9876/docs

## Seed demo data

```bash
python correlation/seed/seed.py
```

## Verify

```bash
bash correlation/seed/verify.sh
```

## Tests

```bash
python -m pytest correlation/tests/ -v
```

## Config

Settings live in `backend/.env` / `backend/config.py`:

- `TSOC_POSTGRES_DSN` — findings store
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` — alert graph
- `CORRELATION_DEMO_API_KEY` — `X-Demo-Api-Key` for `/internal/correlate`
- `TSOC_CORRELATION_ENABLED` — set `false` to disable mount

`correlation/run.py` forwards to `backend/run.py` (no separate port 8012).
