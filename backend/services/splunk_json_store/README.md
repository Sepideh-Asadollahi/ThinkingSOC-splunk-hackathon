# Splunk JSON Store

PostgreSQL-backed JSON event persistence layer. Stores all TSOC records (ingests, analyses, audits) as JSONB documents, provides query and aggregation APIs for the dashboard and triage queue.

## Key files

| File | Description |
|------|-------------|
| `pg.py` | PostgreSQL pool, schema bootstrap, and JSONB insert helpers |
| `query.py` | Read stored TSOC records from PostgreSQL (by ID, filtered search) |
| `stats.py` | PostgreSQL aggregations for dashboard overview |
| `__init__.py` | Re-exports persistence functions and pool management |

## Related docs

- [Storage & Persistence](../../../docs/19-storage-persistence.md)
