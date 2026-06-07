# graph_crud

Data access layer for graph correlation. Handles Neo4j graph operations and PostgreSQL finding persistence.

## Key files

| File | Description |
|------|-------------|
| `alert_upsert.py` | Parses Splunk webhook payloads and upserts Alert + entity nodes into Neo4j |
| `alert_centric.py` | Builds alert-centric topology graphs and attack trees from Neo4j incident data |
| `correlation.py` | Finds correlated alerts by shared entities and historical related incidents in Neo4j |
| `findings.py` | PostgreSQL CRUD for `graph_findings` — list, get, insert, patch ticket, content-hash dedup |
| `incident_sync.py` | Syncs finding incidents to Neo4j — links alerts to incidents and builds CAUSED chains |
| `schema.py` | Ensures the `graph_findings` PostgreSQL table exists and seeds demo data if empty |
| `topology.py` | Thin wrapper that delegates topology building to `alert_centric.py` |

## Related docs

- [Correlation Graph Service](../../docs/12-correlation-graph-service.md)
- [Database Schema](../../docs/21-database-schema.md)
