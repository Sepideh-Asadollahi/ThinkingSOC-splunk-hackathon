# Demo PostgreSQL data (full backup + moment snapshot)

How hackathon **demo data** is bundled, loaded during **`install.sh`**, and refreshed from a live database.

**Related:** [14-inventory-service.md](./14-inventory-service.md) · [12-correlation-graph-service.md](./12-correlation-graph-service.md) (Correlation `graph_findings`) · [21-database-schema.md](./21-database-schema.md) · [install/README.md](../install/README.md) · [backend/data/demo/README.md](../backend/data/demo/README.md)

---

## Primary mechanism: full database backup

To guarantee a **new server gets an identical demo** (the recurring problem with selective snapshots was that they dropped `tsoc_rag_documents` and extra correlation findings), the bundled demo is a **full `pg_dump`** of the `tsoc` database:

```text
backend/data/demo/postgres_dump/tsoc_demo.sql   # pg_dump --clean --if-exists (all tables + data)
```

- **Restore = byte-for-byte replica** of the source server: `tsoc_users`, `tsoc_assets`, `tsoc_relationships`, `tsoc_identity_rules`, **all** `tsoc_records`, **all** `graph_findings` (Correlation), **all** `tsoc_rag_documents` (SOC Chat RAG), and chat tables — including sequence values.
- `install.sh` restores it with `psql` (see below). If the dump is absent, it falls back to the JSON snapshot.

```bash
# Capture (on a dev box with the desired data)
bash scripts/backup-demo-db.sh            # writes backend/data/demo/postgres_dump/tsoc_demo.sql

# Restore on any server (also runs automatically during install.sh)
bash scripts/restore-demo-db.sh           # psql restore + service restart
```

**Always commit `backend/data/demo/postgres_dump/tsoc_demo.sql`** so a fresh GitHub clone restores the same data.

---

## Fallback: JSON moment snapshot

Used only when the full backup is missing.

| Data | Scope in fallback snapshot |
|------|----------------|
| **Asset + Identity** | **Full** — all rows from `tsoc_users`, `tsoc_assets`, `tsoc_relationships`, `tsoc_identity_rules` |
| **Analysis moment** | **Up to 6 newest** rows from `tsoc_records` (by `id`, the monotonic PK — robust against clustered `created_at`) |
| **Correlation** | **Newest 1** row from `graph_findings` (`/correlation`) |
| **Not in snapshot** | `tsoc_rag_documents`, chat (RAG may backfill at runtime) |

```text
backend/data/demo/postgres_snapshot/
├── manifest.json
├── tsoc_users.json
├── tsoc_assets.json
├── tsoc_relationships.json
├── tsoc_identity_rules.json
├── tsoc_records.json
└── graph_findings.json
```

---

## Automatic load (`install.sh`)

When the installer asks **Load demo data?** and you answer **Yes** (default):

1. **No extra apt packages** — uses Docker PostgreSQL (`tsoc-postgres`); restore runs with the container's `psql`.
2. **`install/modules/demo_data.sh`** copies `postgres_dump/` (and the JSON `postgres_snapshot/` fallback) into `INSTALL_DIR` when needed.
3. **`setup.py`** runs schema + a baseline seed.
4. **`install.sh`** then restores the **full backup** (`docker exec -i tsoc-postgres psql … < tsoc_demo.sql`) — this `DROP`s and recreates every table with the source data — and **automatically restarts** `tsoc-backend` / `tsoc-frontend` before the smoke test (no manual restart). If the dump is missing it applies the JSON snapshot instead.
5. A **final automatic restart** runs at the end of install (after the optional integration wizard) so `.env` changes are active.

**Install directory:**

| How you start | `INSTALL_DIR` |
|---------------|---------------|
| `curl … \| sudo bash` (one-liner) | `/opt/thinking-soc-splunk-hackathon` (bootstrap clones first) |
| `sudo bash install.sh` from a checkout | That checkout (unless `TSOC_INSTALL_DIR` is set) |

**Existing Docker stack:** If old `tsoc-postgres` / `tsoc-qdrant` / `tsoc-neo4j` containers or volumes are detected, the installer asks before deleting that data (images are kept). A fresh stack is started before demo seed runs. When using a custom path, set `TSOC_INSTALL_DIR=/path/to/clone` and ensure that tree contains `backend/data/demo/postgres_dump/` or `postgres_snapshot/`.

Skip demo seed: answer **No**, or run `setup.py` with **`--no-seed`**.

---

## Manual setup (`setup.py`)

From repo root (Docker Postgres running):

```bash
backend/.venv/bin/python setup.py --skip-docker -v
# Skip demo: add --no-seed
```

Same restore path as install: snapshot first, then CSV fallback under `backend/data/demo/`.

Verify after seed:

```bash
docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc "SELECT COUNT(*) FROM tsoc_users;"
docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc "SELECT COUNT(*) FROM tsoc_records;"
# Expect 7 users and 4 records for the bundled moment snapshot
```

---

## Automatic service restart

The installer never asks you to restart manually for demo data. After PostgreSQL is seeded it reloads backend + frontend (systemd or background scripts). The helper `scripts/reload-demo-snapshot.sh` also restarts services when run on its own.

---

## Refresh snapshot from live DB

After you change inventory or run new analyses on a dev machine:

```bash
cd backend && .venv/bin/python scripts/seed/export_demo_postgres_snapshot.py
# Default: full Asset/Identity + up to 6 newest records + newest correlation finding
# Optional: --record-limit 8
```

Commit the updated `backend/data/demo/postgres_snapshot/` files so the next install loads the new moment.

---

## Implementation map

| Component | Role |
|-----------|------|
| `scripts/backup-demo-db.sh` | Capture full `pg_dump` → `postgres_dump/tsoc_demo.sql` |
| `scripts/restore-demo-db.sh` | Restore full backup with `psql` (any server) |
| `install/modules/demo_data.sh` | Restore dump first (`_restore_demo_dump_to_postgres`), JSON snapshot fallback |
| `services/demo/postgres_snapshot.py` | Fallback: export / restore JSON + `manifest.json` |
| `services/splunk_json_store/pg.py` | Calls JSON restore on `init_store()` when DB empty |
| `setup_tool/seed.py` | Install-time baseline seed step |
| `scripts/seed/export_demo_postgres_snapshot.py` | JSON snapshot export CLI |

---

## CSV fallback (legacy / scenarios)

If `postgres_snapshot/manifest.json` is missing, seed uses merged CSVs:

- Root: `backend/data/demo/tsoc_*.csv`
- Scenario packs: `botsv1_osk_sysmon/`, `attacks_t8372/`, `observability_cpu_latency/`

See [backend/data/demo/README.md](../backend/data/demo/README.md).
