# seed

Seed data and database fixtures for the correlation demo. Populates PostgreSQL `graph_findings` and the Neo4j alert/incident graph with the "Operation Shadow Login" campaign. **Attack Discovery** itself does not hardcode these alert IDs — it uses entity prefixes and graph structure ([`graph_core/entity_taxonomy.py`](../graph_core/entity_taxonomy.py)).

## Key files

| File | Description |
|------|-------------|
| `seed.py` | Entrypoint script — runs PostgreSQL migration + demo inserts and Neo4j Cypher statements |
| `01_graph_findings.sql` | DDL for `graph_findings` table and indexes (idempotent `CREATE TABLE IF NOT EXISTS`) |
| `postgres_demo_findings.sql` | Single demo finding `GF-0007` (Attack Discovery output for Operation Shadow Login) |
| `neo4j_demo_campaign.cypher` | Cypher statements creating demo Alert, Identity, Asset, IOC, and Incident nodes with relationships |
| `verify.sh` | cURL smoke-test script exercising health, correlate, findings, topology, and discover endpoints |

## Related docs

- [Correlation Graph Service](../../docs/12-correlation-graph-service.md)
- [Database Schema](../../docs/21-database-schema.md)
