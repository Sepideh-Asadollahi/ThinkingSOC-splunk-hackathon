# graph_core

Core infrastructure layer for the correlation service. Manages database connections and shared utilities used by CRUD and pipeline modules.

## Key files

| File | Description |
|------|-------------|
| `neo4j_driver.py` | Async Neo4j driver singleton — connect, close, reset, read/write query helpers |
| `postgres_pool.py` | Async PostgreSQL connection pool (asyncpg) — init, close, reset, raw SQL execution |
| `neo4j_sanitize.py` | Recursively converts Neo4j native types (dates, nested dicts) to JSON-safe values |
| `operation_store.py` | In-memory async operation tracker for long-running analysis tasks (create/log/complete/fail) |
| `entity_taxonomy.py` | Classify `type:value` entity identifiers as anchor / indicator / other for Attack Discovery (no alert-specific hardcoding) |

## Related docs

- [Correlation Graph Service](../../docs/12-correlation-graph-service.md)
- [Database Schema](../../docs/21-database-schema.md)
