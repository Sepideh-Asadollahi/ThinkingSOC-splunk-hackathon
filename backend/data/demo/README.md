# Demo data (PostgreSQL)

**Public guide:** [docs/24-demo-postgresql-data.md](../../../docs/24-demo-postgresql-data.md) · **Correlation docs:** [docs/12-correlation-graph-service.md](../../../docs/12-correlation-graph-service.md) · **Installer:** [install/README.md](../../../install/README.md) (demo load = Docker + Python `asyncpg`, no extra apt tools)

Demo data is loaded in this order:

0. **`postgres_dump/tsoc_demo.sql`** — **primary**: full `pg_dump` backup of the demo DB. `install.sh` restores it with `psql` (`DROP` + recreate every table with data), so a new server is an exact replica — inventory, **all** `tsoc_records`, **all** `graph_findings`, **all** `tsoc_rag_documents`. Capture: `bash scripts/backup-demo-db.sh`; restore: `bash scripts/restore-demo-db.sh`.
1. **`postgres_snapshot/`** — JSON fallback (moment snapshot) when the dump is absent and `manifest.json` is present:
   - **Full** Asset + Identity: `tsoc_users`, `tsoc_assets`, `tsoc_relationships`, `tsoc_identity_rules`
   - **Up to 6 newest** `tsoc_records` by `id` (latest analysis moment only)
   - **Newest 1** `graph_findings` row (Correlation page)
2. **CSV fallback** — `tsoc_*.csv` at repo root and scenario subdirectories (see below).

Refresh the snapshot from a running database (full inventory + up to 6 newest records + newest correlation finding):

```bash
cd backend && .venv/bin/python scripts/seed/export_demo_postgres_snapshot.py
# Optional: --record-limit 4
```

## `postgres_snapshot/`

| File | Contents |
|------|----------|
| `manifest.json` | Table list and row counts |
| `*.json` | One JSON array per table |

Restore logic: `services/demo/postgres_snapshot.py`.

## Inventory CSVs (fallback)

| Location | Purpose |
|----------|---------|
| `tsoc_users.csv` (root) | Baseline hackathon users/assets |
| `tsoc_assets.csv` / `tsoc_relationships.csv` (root) | Same |
| `botsv1_osk_sysmon/` | BOTS v1 Sysmon scenario inventory |
| `attacks_t8372/` | ATTACKS kill-chain scenario inventory |
| `observability_cpu_latency/` | Observability CPU/latency scenario inventory |

**CSV merge:** `services/inventory/csv_seed.py` loads root CSVs first, then scenario subdirectories (sorted). Rows dedupe on `user_id`, `asset_id`, or `relationship_id` (first file wins).

**Auto-relationships:** `services/inventory/default_relationships.py` links assets to users when `asset.owner` matches `user_id`, or `ops` → IT / `dba` → Finance. Explicit `tsoc_relationships.csv` overrides generated links.
