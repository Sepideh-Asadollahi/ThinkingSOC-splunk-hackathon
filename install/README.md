# ThinkingSOC installer — how the stack runs

Default install directory: **`/opt/thinking-soc-splunk-hackathon`**.

```bash
# One-liner: bootstrap.sh → clone repo to /opt → full install
curl -fsSL https://raw.githubusercontent.com/Sepideh-Asadollahi/ThinkingSOC-splunk-hackathon/main/install/bootstrap.sh | sudo bash

# Or from /opt after clone (skips bootstrap)
cd /opt/thinking-soc-splunk-hackathon && sudo bash install.sh
```

### One-liner bootstrap (`install/bootstrap.sh`)

Use **`install/bootstrap.sh`** for `curl | bash` — **not** `install.sh` alone. GitHub raw can cache an old `install.sh` on `/main/` for ~5 minutes after pushes.

When you pipe `bootstrap.sh`:

1. Installs **`git`** via apt if needed.
2. **`git clone`**s (or **`git pull`**s) to **`/opt/thinking-soc-splunk-hackathon`**.
3. **`exec`**s the cloned `install.sh`.

**Requirements:** root (`sudo bash`), HTTPS to GitHub, Ubuntu/Debian with `apt`.

**If you see** `Missing required installer module` after piping **`install.sh`**, switch to **`install/bootstrap.sh`** (one-liner above) or clone manually.

`install.sh` installs Docker, databases, backend, and frontend.

- **One-liner / bootstrap:** always uses **`/opt/thinking-soc-splunk-hackathon`** (unless `TSOC_INSTALL_DIR` is set).
- **Run from an existing checkout:** uses that checkout as `INSTALL_DIR` unless `TSOC_INSTALL_DIR` overrides it.

Both modes use a **production** frontend: `npm run build` then `npm run start` (`next start`).  
They do **not** use `npm run dev` (dev/HMR is only for local UI development).

| | Backend API | Frontend UI | Demo login |
|--|-------------|-------------|------------|
| URL | `http://127.0.0.1:9876` (localhost) | `http://<server-ip>:3000` | `admin` / `123456@a` |

Docker must stay up: `tsoc-postgres`, `tsoc-qdrant`, `tsoc-neo4j`.

### Demo data (full snapshot)

If you answer **Yes** to **Load demo data** during `install.sh`:

- **No extra apt packages** are required (no `postgresql-client`, `pg_dump`, or `jq` on the host).
- The installer already provides **Docker PostgreSQL** and **Python `asyncpg`** in `backend/.venv`.
- Data is restored automatically from the full backup `backend/data/demo/postgres_dump/tsoc_demo.sql` (a `pg_dump` replica: inventory, all `tsoc_records`, all `graph_findings`, all `tsoc_rag_documents`, and Chat). Falls back to the full JSON snapshot under `backend/data/demo/postgres_snapshot/` if the backup is missing.
- The restored data includes the additive **Judge Demo: Suspicious OAuth Token Replay** tour: same-name/different-SID alerts, source-verified Runbook, human approval, Shadow Run, safe-response preview, five-agent Autopilot trace, and a preloaded Chat/RAG guide. Existing demo scenarios remain present.
- Fallback: CSV files under `backend/data/demo/` if the snapshot bundle is missing.

Refresh the bundled snapshot after changing a live database:

```bash
bash scripts/backup-demo-db.sh --json-full
```

**Full documentation:** [docs/24-demo-postgresql-data.md](../docs/24-demo-postgresql-data.md)

**Troubleshooting “manifest not found”:** Ensure the install tree at `/opt/thinking-soc-splunk-hackathon` contains `backend/data/demo/postgres_snapshot/` (re-clone or `git pull`). The installer copies bundled demo files into `INSTALL_DIR` before `setup.py` when paths differ.

**UI empty after install?** Re-run (reloads Postgres and restarts services automatically):

```bash
sudo bash /opt/thinking-soc-splunk-hackathon/scripts/reload-demo-snapshot.sh
```

During `install.sh`, demo load + service restart run automatically when you choose **Load demo data**.

The install Smoke Test also performs a non-destructive restore of both the SQL dump and JSON fallback into temporary databases. It verifies all 14 persisted SOC runner pipeline record types, confirms they are available through the authenticated frontend proxy, preserves previous demo scenarios, and checks that the Runbook judge tour includes same-name/different-SID reuse, three parser-valid evidence steps, human approval, Shadow Run, five-agent Autopilot trace, safe response preview, Chat/RAG content, and SPL syntax self-repair. The temporary databases are always removed afterward. Run this check again at any time:

```bash
sudo bash install/smoke-demo-data.sh
```

**Troubleshooting empty Analysis/Correlation on a new server:** read the installer's demo restore log:

```bash
cat "$INSTALL_DIR/logs/demo-restore.log"
# psql stderr (if dump restore failed):
cat "$INSTALL_DIR/logs/demo-restore-psql.log"
```

The log lists which restore mode was used (`dump` vs JSON snapshot vs CSV), whether `backend/data/demo/postgres_dump/tsoc_demo.sql` was present, row counts before/after restore, and warnings if `analyses=0` or `graph_findings=0`.

### Docker stack reset (existing install)

If **tsoc-postgres**, **tsoc-qdrant**, or **tsoc-neo4j** (or their data volumes) already exist, the installer **asks for confirmation** before:

- Stopping and removing those containers and **all ThinkingSOC data volumes** (PostgreSQL / Qdrant / Neo4j data on the host)
- **Keeping** Docker images (no re-download from Docker Hub unless an image was missing)
- Starting a fresh stack with `docker compose up -d`

If nothing is detected, no prompt — a new stack is created automatically.

**Canonical Docker names** (same in `backend/docker-compose.yml`, `setup_tool/docker.py`, installer):

| Kind | Names |
|------|--------|
| Containers | `tsoc-postgres`, `tsoc-qdrant`, `tsoc-neo4j` |
| Data volumes | `tsoc_pgdata`, `tsoc_qdrant_data`, `tsoc_neo4j_data` |
| Compose project | `tsoc` |

Older installs may have left `backend_tsoc_*` volumes; the installer removes those too when resetting.

For an unattended CI or disposable-server smoke test, the same safety decision
must be explicit; it is never inferred from `NON_INTERACTIVE=true`:

```bash
sudo env \
  NON_INTERACTIVE=true \
  TSOC_LOAD_DEMO_DATA=true \
  TSOC_SETUP_SYSTEMD=false \
  TSOC_RESET_EXISTING_STACK=true \
  TSOC_INSTALL_STATE_FILE=/tmp/tsoc-clean-install.progress \
  bash install.sh
```

`TSOC_RESET_EXISTING_STACK=true` removes only the named ThinkingSOC containers
and volumes listed above. Do not set it when the current ThinkingSOC database
must be preserved.

### Vector embedding model download (default `bge-base`, ~220 MB)

Before starting the backend, the installer downloads the **FastEmbed** ONNX model used for SOC Chat / RAG.  
**Default on fresh install:** `bge-base` (**medium**, ~**220 MB**). Use `bge-large` (~1.2 GB) only when you change `TSOC_EMBEDDING_MODEL` in `backend/.env`. You will see:

- A message that the download is in progress and may take a long time on slow networks  
- A **progress bar** based on cache directory size under `/opt/.thinking-soc-cache/fastembed`  
- Log file: `logs/embedding-download.log`

The API answers **`GET /health` soon after start**; the embedding model continues loading in the **background** (SOC Chat/RAG). Smoke test waits up to ~6 minutes if needed.

If install warns on backend health, check `sudo journalctl -u tsoc-backend -n 80` or pre-download manually:

```bash
bash scripts/download-embedding-model.sh              # bge-base (~220 MB, install default)
bash scripts/download-embedding-model.sh bge-small   # ~33 MB (slow networks)
bash scripts/download-embedding-model.sh bge-large   # ~1.2 GB (best quality)
```

---

## Choice during `install.sh`

Step **Service deployment (systemd)** asks:

**Create systemd services (tsoc-backend + tsoc-frontend)?** (default: **Yes**)

| Answer | What install does |
|--------|-------------------|
| **Yes** | Creates systemd units, enables auto-start on boot, starts services |
| **No** | Starts backend + frontend in the background under `logs/` |

At the end of install, a **command cheat sheet** for your choice is printed.

---

## Post-install integration wizard (Splunk, LiteLLM, MCP)

Immediately after the main installer summary, an **optional wizard** runs (default: **Yes**). It configures external integrations and **verifies they work** with a live smoke test.

**Full documentation:** [docs/23-post-install-integration-wizard.md](../docs/23-post-install-integration-wizard.md)

### Quick commands

```bash
# Re-run the full wizard (root)
sudo bash scripts/configure-integration.sh

# Live verification only (smoke test)
sudo bash install/smoke-integration-config.sh
bash scripts/configure-integration.sh --smoke
```

### What the wizard does

1. **Prompts:** `SPLUNK_HOME`, Splunk REST URL/credentials, LiteLLM **model** + **API key** (required), optional ingest token.  
2. **Writes:** `backend/.env`, `frontend/.env.local` (includes `TSOC_INGEST_AUTO_ANALYZE=true` for auto triage after Splunk/webhook ingest).  
3. **Splunk:** Copies `ThinkingSOC_Hackathon_Splunk_App`; runs `scripts/setup_splunk_mcp.py` (app 7931, `mcp_tool_execute` RBAC, MCP token).  
4. **Restarts** `tsoc-backend` and `tsoc-frontend` automatically so `.env` / `.env.local` load (no prompt).  
5. **Smoke test:** Splunk REST login, `GET /health`, `GET /api/v1/mcp/status` — confirms integration works **now**.  
6. **Prints** masked `.env` summary for manual edits.  
7. **Reminds** you to run `$SPLUNK_HOME/bin/splunk restart` after app/MCP changes.

After the wizard (or if you skipped it), `install.sh` runs a **final mandatory restart** of both services and verifies `/health` and `/login`. On failure it prints manual restart commands.

### Post-configure modules

Code under `install/modules/post_configure/` (loader: `post_configure.sh`):

| Module | Role |
|--------|------|
| `helpers.sh` | Prompts, `.env` reads, Splunk path/URL parsing |
| `litellm.sh` | `LITELLM_MODEL` picker (default = current `.env`) |
| `env_apply.sh` | Write `backend/.env` + `frontend/.env.local` |
| `splunk_app.sh` | Copy `ThinkingSOC_Hackathon_Splunk_App` |
| `mcp.sh` | Splunk MCP via `scripts/setup_splunk_mcp.py` |
| `restart.sh` | Restart `tsoc-backend` + `tsoc-frontend`, verify, manual-restart hints |
| `smoke_probes.sh` | Live Splunk REST + MCP API probes |
| `smoke.sh` | `run_integration_configure_smoke` |
| `summary.sh` | Print integration `.env` keys + Splunk restart reminder |
| `wizard.sh` | `run_post_install_configure` |

### Scripts (repo root)

| Script | Purpose |
|--------|---------|
| `scripts/configure-integration.sh` | Wizard entrypoint |
| `scripts/setup_splunk_mcp.py` | Install/enable MCP app on Splunk + mint token |
| `scripts/mint_splunk_mcp_token.py` | Mint MCP token only |
| `install/smoke-integration-config.sh` | Smoke test only |

Skip wizard during install: `NON_INTERACTIVE=true sudo bash install.sh`

---

## Mode 1 — With systemd (recommended)

**Units**

| Unit | Process | Port |
|------|---------|------|
| `tsoc-backend` | `backend/.venv/bin/python run.py` | `9876` |
| `tsoc-frontend` | `next start -H 0.0.0.0 -p 3000` | `3000` |

**Files:** `/etc/systemd/system/tsoc-backend.service`, `tsoc-frontend.service`

### Manage

```bash
# Status & health
sudo systemctl status tsoc-backend tsoc-frontend
curl -s http://127.0.0.1:9876/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/login

# Start / stop / restart
sudo systemctl start tsoc-backend tsoc-frontend
sudo systemctl stop tsoc-frontend tsoc-backend
sudo systemctl restart tsoc-backend tsoc-frontend

# Boot on / off
sudo systemctl enable tsoc-backend tsoc-frontend
sudo systemctl disable tsoc-backend tsoc-frontend

# Logs
sudo journalctl -u tsoc-backend -f
sudo journalctl -u tsoc-frontend -f
```

### After UI code changes

```bash
cd /opt/thinking-soc-splunk-hackathon/frontend   # your INSTALL_DIR
npm run build
sudo systemctl restart tsoc-frontend
```

---

## Mode 2 — Without systemd (background)

**Processes** (PIDs in `logs/backend.pid`, `logs/frontend.pid`)

| Log | Command |
|-----|---------|
| `logs/backend.log` | `backend/.venv/bin/python run.py` |
| `logs/frontend.log` | `npm run start` (production) |

### Manage

```bash
INSTALL_DIR=/opt/thinking-soc-splunk-hackathon   # your path

# Start or restart (builds .next if missing)
sudo bash "$INSTALL_DIR/scripts/start-tsoc-services.sh"

# Logs
tail -f "$INSTALL_DIR/logs/backend.log" "$INSTALL_DIR/logs/frontend.log"

# Health
curl -s http://127.0.0.1:9876/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/login
```

### After UI code changes

```bash
cd "$INSTALL_DIR/frontend" && npm run build
sudo bash "$INSTALL_DIR/scripts/start-tsoc-services.sh"
```

### Switch to systemd later

```bash
sudo bash "$INSTALL_DIR/scripts/install-systemd.sh"
```

(Same as answering **Yes** during `install.sh`.)

---

## Enable systemd if you chose No during install

```bash
cd /opt/thinking-soc-splunk-hackathon
sudo bash scripts/install-systemd.sh
```

---

## More documentation

- Repository [README.md](../README.md) — full project setup, Splunk, troubleshooting  
- [Post-install integration wizard](../docs/23-post-install-integration-wizard.md) — Splunk / LiteLLM / MCP / smoke test  
- [Environment configuration](../docs/11-environment-configuration.md) — all `.env` variables  
- [Service control with systemd](../README.md#service-control-with-systemd)  
- [Production services (no systemd)](../README.md#production-services-no-systemd)

**Installer help without running install:** `sudo bash install.sh --help`
