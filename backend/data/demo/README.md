# Demo data (PostgreSQL)

**Public guide:** [docs/24-demo-postgresql-data.md](../../../docs/24-demo-postgresql-data.md) · **Correlation docs:** [docs/12-correlation-graph-service.md](../../../docs/12-correlation-graph-service.md) · **Installer:** [install/README.md](../../../install/README.md) (demo load = Docker + Python `asyncpg`, no extra apt tools)

Demo data is loaded in this order:

0. **`postgres_dump/tsoc_demo.sql`** — **primary**: full `pg_dump` backup of the demo DB. `install.sh` restores it with `psql` (`DROP` + recreate every table with data), so a new server is an exact replica — inventory, **all** `tsoc_records`, **all** `graph_findings`, **all** `tsoc_rag_documents`, and Chat history. Capture: `bash scripts/backup-demo-db.sh`; restore: `bash scripts/restore-demo-db.sh`.
1. **`postgres_snapshot/`** — full JSON fallback when the dump is absent and `manifest.json` is present. The committed manifest contains every row from inventory, records, RAG, correlation, and Chat tables.
2. **CSV fallback** — `tsoc_*.csv` at repo root and scenario subdirectories (see below).

## Installed Runbook judge tour

The full dump and JSON fallback include an additive, fully linked synthetic scenario named **`Judge Demo: Suspicious OAuth Token Replay`**. It does not replace any previous demo row and contains:

- two `soc_analysis` alerts with the exact same Alert Name and different stable SIDs;
- analyst acknowledgement, a three-step `SOURCE_VERIFIED` Runbook, and recorded human approval;
- an evidence-bearing Shadow Run and an approved `REUSED` run against the second SID;
- a `PREVIEW_ONLY` Safe Response plus a decision whose automatic-execution flag is false;
- a five-agent Runbook Autopilot trace covering MCP, REST fallback, compiler, policy, and response-advisor tools;
- compact RAG documents and a **Judge tour — Runbook Autopilot** Chat conversation.

All identities, applications, addresses, timestamps, and evidence rows in this tour are synthetic. Rebuild or verify it idempotently without deleting other data:

```bash
backend/.venv/bin/python backend/scripts/seed/seed_runbook_judge_demo.py
```

Refresh the full JSON snapshot from a running database:

```bash
cd backend && .venv/bin/python scripts/seed/export_demo_postgres_snapshot.py --full
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
