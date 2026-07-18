# Backend (FastAPI)

**Splunk version:** the REST client is written for **Splunk 10+** (uses v2 job results API by default).

Source layout: Python packages live **directly under `backend/`** (`main.py`, `config.py`, `api/`, `models/`, `services/`, `splunk/`).

## One-time setup (root of repo)

Checks dependencies and applies PostgreSQL schema (does **not** start the API):

```bash
cd /opt/thinking-soc-splunk-hackathon
python setup.py --start-postgres
```

## Quick start (no Docker for backend)

**1. PostgreSQL in Docker** (data store only):

```bash
cd /opt/thinking-soc-splunk-hackathon/backend
docker-compose up -d
```

**2. Python env and config:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — TSOC_POSTGRES_DSN=postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc
```

**3. Run API on the host:**

```bash
python run.py
```

`run.py` prefers `backend/.venv` when present (falls back to `/opt/ThinkingSOC Lite/backend/.venv` if installed).

Optional: `TSOC_HTTP_HOST` (default `127.0.0.1`), `TSOC_HTTP_PORT` (default `9876`), `TSOC_RELOAD=1` for development.

Copy `.env.example` to `.env` and set Splunk credentials, PostgreSQL DSN, and optional ingest token. The Splunk client calls **`GET /services/search/v2/jobs/{sid}/results`** for job rows (Splunk **10+** only). Full variable reference: [../docs/11-environment-configuration.md](../docs/11-environment-configuration.md).

### LiteLLM (`.env`)

All LLM calls go through **LiteLLM** (`services/llm/litellm_service.py`). Configure model, keys, timeout, RPM, retry/backoff, and token limits in **`backend/.env`** (see `.env.example`): `LITELLM_MODEL`, `LITELLM_API_KEY` / `LITELLM_API_BASE`, `LITELLM_TIMEOUT_SECONDS`, `LITELLM_RPM` (default `30`), `LITELLM_MAX_RETRIES` (default `3`), `LITELLM_RETRY_BASE_SECONDS`, `LITELLM_RETRY_MAX_SECONDS`, `LITELLM_ANALYSIS_MAX_TOKENS`, `LITELLM_ANALYSIS_TEMPERATURE`, optional `LITELLM_CHAT_DEFAULT_TEMPERATURE`. Explicit environment / `.env` values take precedence over persisted Integration Settings; persisted values fill only unset fields. Transient provider overload, rate-limit, timeout, and network failures are retried with bounded exponential backoff; permanent request/authentication errors fail immediately. SOC/Observability pipelines fall back to rule-based stages after retry exhaustion. `GET /api/v1/llm/status` returns non-secret settings. Structure: [../docs/04-agents-and-pipelines.md](../docs/04-agents-and-pipelines.md).

**Storage (PostgreSQL):** backend writes ingest/analysis/audit JSON records into PostgreSQL (`TSOC_POSTGRES_DSN`).

### VirusTotal (optional)

Set `VIRUSTOTAL_API_KEY` in `.env` to enrich IOCs during SOC analysis (`virustotal` graph node). See [../docs/09-virustotal-threat-intel.md](../docs/09-virustotal-threat-intel.md) for API v3 field mapping, compact output, and tests:

```bash
.venv/bin/pytest tests/test_virustotal.py tests/test_virustotal_schema.py tests/test_threat_intel_compact.py -q
```

## Manual uvicorn (alternative)

```bash
cd /opt/thinking-soc-splunk-hackathon/backend
source /opt/ThinkingSOC Lite/backend/.venv/bin/activate
export PYTHONPATH=.
uvicorn main:app --host 127.0.0.1 --port 9876
```

## Docker (PostgreSQL + Qdrant)

`docker-compose.yml` runs **postgres** (`5432`) and **[Qdrant](https://github.com/qdrant/qdrant)** (`6333`) for semantic RAG. Embeddings run on the host via **FastEmbed** (`python run.py`). See [docs/10-soc-vector-rag.md](../docs/10-soc-vector-rag.md).

Clean up old RAGFlow images: `bash scripts/docker-cleanup-unused.sh`

## Unit tests

From `backend/` (uses ThinkingSOC Lite venv which includes `pytest`). Unit/API tests are **fast by default** and do **not** run external startup (Splunk login, embeddings/RAG warmup, correlation startup).

```bash
cd /opt/thinking-soc-splunk-hackathon/backend
source /opt/ThinkingSOC Lite/backend/.venv/bin/activate
pytest
```

### Opt-in: real FastAPI startup during tests

Some integration-style checks may need the real `main.py` lifespan. Opt-in via the `real_startup` marker:

```bash
cd /opt/thinking-soc-splunk-hackathon/backend
pytest -m real_startup -v -s
```

### Opt-in: live Splunk MCP/SAIA tests

Live Splunk tests are separately marked `splunk_live` and require `TSOC_RUN_SPLUNK_LIVE=1` plus valid Splunk credentials/config.

## Endpoints

- `GET /health`
- `POST /api/v1/alerts/splunk-ingest` — JSON handoff from Splunk alert action (`result` + optional `results[]`; Bearer if `TSOC_INGEST_TOKEN` set). Returns `202` when `TSOC_INGEST_AUTO_ANALYZE=true` (default), else `200`. **Configuration is not overridable via URL query parameters.** Multi-row jobs: row buffer per `sid` → REST enrich → **sequential per-row triage** (storage `sid` suffix `-1`, `-2`, …); see [docs/02-integration-boundaries.md](../docs/02-integration-boundaries.md).
- `POST /api/v1/classification/alert` — LLM classify into `security|observability|unknown` → `recommended_pipeline` is `security`, `observability`, or `manual_review` (exclusive — never both pipelines; optional `sid` enrichment)
- `GET /api/v1/llm/status` — LiteLLM config surface (no secrets); see [docs/04-agents-and-pipelines.md](../docs/04-agents-and-pipelines.md)
- `POST /api/v1/llm/chat` — chat completion via LiteLLM (`messages` array); same Bearer rule as ingest when `TSOC_INGEST_TOKEN` is set
- `POST /api/v1/assistant/spl-suggest` — SPL via REST `/predict` (UI path), MCP execute (All Time), LiteLLM/rule fallback — [docs/13-cim-investigation-spl-mcp.md](../docs/13-cim-investigation-spl-mcp.md)
- SOC **`investigation_questions`** — `/predict` per question, deterministic syntax repair, MCP `splunk_run_query`, refine loop (max 3) → `spl_results` in UI — [docs/13-cim-investigation-spl-mcp.md](../docs/13-cim-investigation-spl-mcp.md)
- `GET /api/v1/mcp/status` — MCP connectivity — [docs/02-integration-boundaries.md](../docs/02-integration-boundaries.md)
- `POST /api/v1/mcp/spl-generate` — debug: MCP `saia_generate_spl` only (not the main investigation path; Bearer if `TSOC_INGEST_TOKEN` set)
- `POST /api/v1/mcp/tools/call` — debug MCP tool invocation by name (Bearer if token set)
- `GET /api/v1/inventory/status` — PostgreSQL inventory configured
- `POST /api/v1/inventory/enrich` — match alert fields to users/assets (optional offline `users` + `assets` + `relationships`)
- `GET/POST/PATCH/DELETE /api/v1/inventory/users` and `/inventory/assets` — inventory CRUD
- `GET/POST/PATCH/DELETE /api/v1/inventory/relationships` — user–asset relationship CRUD
- `POST /api/v1/analysis/run` — full SOC analysis (enrichment + Defender / Hunter / Judge + risk + MITRE-style mapping). LangGraph pipeline via LiteLLM with rule-based fallback on error. Optional offline triple (`users`, `assets`, `relationships`) for tests.
- `POST /api/v1/analysis/route` — classify and run Security/Observability pipeline(s) automatically
- `POST /api/v1/agents/triage` — agent-style triage orchestration (route + pipeline + next actions + suggested SPL); response includes `security_triage` / `observability_triage` when pipelines run
- `GET /api/v1/triage/queue` — analyst queue sorted by `triage_score`, with pipeline and limit filtering; see [docs/08-triage-priority-layer.md](../docs/08-triage-priority-layer.md)
- `POST /api/v1/analysis/run-by-sid` — fetch all rows for a Splunk `sid`, run analysis per row.
- `POST /api/v1/observability/run` — run Observability pipeline directly (enrichment + Diagnoser + Responder + Ops Judge)
- `POST /api/v1/observability/run-by-sid` — fetch rows for a Splunk `sid`, run Observability per row
- `GET /api/v1/storage/events` — search JSON records stored in PostgreSQL (optional `sid`, `record_type`)
- `GET /api/v1/investigation/runbook-settings` — non-secret ThinkingSOC Lite policy and dependency readiness
- `GET /api/v1/investigation/runbooks`, `/export`, `POST /import`, and `PATCH /runbooks/{runbook_id}` — Alert Name library, portable JSON exchange, and immutable revision editing
- `POST/GET /api/v1/investigation/records/{record_id}/runbook` — compile/source-verify or load the latest verified-runbook state
- `POST/GET /api/v1/investigation/records/{record_id}/runbook/autopilot` — run or inspect bounded Supervisor/Evidence/Engineer/Guard/Advisor collaboration with durable Tool traces; never auto-approves or executes containment
- `GET /api/v1/investigation/records/{record_id}/runbook/compatible-targets` — bounded, payload-free exact-detection candidates for guided reuse
- `POST /api/v1/investigation/records/{record_id}/runbook/approval` and `POST /api/v1/investigation/records/{target_record_id}/runbook-runs` — human decision and read-only reuse
- Runbook SPL execution uses `TSOC_SPL_EXECUTE_VIA_MCP=true` as **MCP preferred, Splunk REST oneshot fallback**. `spl_results.execution_transport` reports `mcp` or `rest`; both error causes are retained if fallback also fails.
- `POST /api/v1/admin-org/gap-suggest` — given alert + optional analysis excerpts, suggest **one organizational GAP question** for an admin (LiteLLM with rule fallback when unavailable). Simplified vs ThinkingSOC Lite `admin_org_gap` (no DB/RAG/queue).
- After every successful **SOC analysis** (`run_analysis`, including ingest auto-triage), the backend also runs admin-org GAP and returns it on `SocAnalysisResult.admin_org_gap` (and stores `admin_org_gap_suggest` when PostgreSQL is configured). The investigation UI shows the suggested admin question when `should_suggest_question` is true.
- `GET /api/v1/soc/chat/status` — RAG index stats (PostgreSQL + Qdrant)
- `POST /api/v1/soc/chat` — SOC analyst chat, including explicit English commands to run the latest approved exact-Alert-Name Runbook for a supplied SID; investigation remains read-only ([docs/10-soc-vector-rag.md](../docs/10-soc-vector-rag.md))
- `POST /api/v1/soc/rag/backfill` — rebuild RAG index from alerts, analyses, inventory/correlation, and all ThinkingSOC Lite Runbook/Autopilot artifacts

### SOC Chat / vector RAG (default)

```bash
cd backend && docker compose up -d   # postgres + qdrant
# .env: TSOC_POSTGRES_DSN, TSOC_VECTOR_ENABLE=true, QDRANT_URL=http://127.0.0.1:6333
```

- `GET /api/v1/soc/chat/status` — Qdrant health + document count + active embedding model
- `POST /api/v1/soc/chat` — semantic retrieval (Qdrant) + LiteLLM
- `POST /api/v1/soc/rag/backfill` — rebuild index from stored Splunk/analysis rows

**Embedding model** — set `TSOC_EMBEDDING_MODEL` in `backend/.env` (see commented options in `.env.example` and [docs/10-soc-vector-rag.md](../docs/10-soc-vector-rag.md#embedding-model-selection)):

| Preset | Download | Dim | Use when |
|--------|----------|-----|----------|
| `bge-small` | ~33 MB | 384 | Dev, slow internet |
| `bge-base` | ~220 MB | 768 | Balance |
| `bge-large` | ~1.2 GB | 1024 | Best quality; slow download |

Pre-download: `bash scripts/download-embedding-model.sh bge-small`. After switching models, restart the API and run backfill if Qdrant dimension changed.

## Developer tools

Simple SDK and CLI for rapid integration/testing:

- SDK: `backend/devtools/` (`TsocSdkClient`, `AsyncTsocSdkClient`, typed models, retries, typed errors)
- CLI: `python backend/devtools/cli.py --help`
- Examples: `backend/devtools/examples/*.json`
- Devtools docs: `backend/devtools/README.md`
- Evaluation runner: `python backend/devtools/evaluate.py --matrix backend/devtools/examples/eval_matrix.json`
- Optional package install: `cd backend/devtools && pip install -e .`

Demo data lives under [`backend/data/demo/`](../backend/data/demo/). On empty PostgreSQL (`install.sh` with demo data, `setup.py`, or first API startup):

0. **`postgres_dump/tsoc_demo.sql`** — full `pg_dump` backup (primary; restored on install via `psql`, replicates the whole demo DB)
1. **`postgres_snapshot/`** — JSON fallback: full Asset/Identity + up to 6 newest `tsoc_records` + newest correlation finding (moment demo)
2. **CSV fallback** — merged `tsoc_*.csv` and scenario subdirs if no snapshot manifest

Export from a live DB: `scripts/seed/export_demo_postgres_snapshot.py`. See [docs/24-demo-postgresql-data.md](../docs/24-demo-postgresql-data.md) and [data/demo/README.md](data/demo/README.md).
