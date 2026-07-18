# Environment configuration

Runtime settings for the hackathon demo are loaded from **environment variables** (and optional `.env` files). This document is the **public reference** for judges and operators; the canonical templates are:

| File | Role |
|------|------|
| [`backend/.env.example`](../backend/.env.example) | Backend API — copy to `backend/.env` |
| [`frontend/.env.example`](../frontend/.env.example) | Next.js UI — copy to `frontend/.env.local` |

**Never commit** `.env`, `.env.local`, or real API keys. Field names match [`backend/config.py`](../backend/config.py) (`Settings` via pydantic-settings, `UPPER_SNAKE_CASE`).

Some built-in keys can be set at runtime through the **Integrations** API (`services/platform/integration_settings.py`). Explicit process environment variables and values present in `backend/.env` are authoritative and take precedence. A persisted Integration setting is used only when that field is absent from env / `.env`.

**URL query parameters cannot override configuration.** The backend returns HTTP `400` if a request includes env-style query keys (e.g. `?auto_analyze=true`, `?TSOC_INGEST_AUTO_ANALYZE=false`). Use `backend/.env` or admin integration settings only.

```mermaid
flowchart TB
  subgraph backendEnv ["backend/.env"]
    HTTP["HTTP & Process\nTSOC_HTTP_HOST, PORT, RELOAD"]
    SplunkREST["Splunk REST\nSPLUNK_MGMT_URL, USERNAME, PASSWORD"]
    PG["PostgreSQL\nTSOC_POSTGRES_DSN"]
    Neo4j_E["Neo4j\nNEO4J_URI, USER, PASSWORD"]
    Ingest["Webhook & Routing\nTSOC_INGEST_TOKEN, AUTO_ANALYZE\nTSOC_CLASSIFIER_LLM"]
    LLM["LiteLLM\nLITELLM_MODEL, API_KEY"]
    MCP_E["MCP & SAIA\nTSOC_MCP_ENABLED, SPLUNK_MCP_URL\nTSOC_MCP_HUNTER_JUDGE_ENABLED"]
    SPL["Investigation SPL\nTSOC_SPL_USE_REST_PREDICT\nTSOC_EXECUTE_INVESTIGATION_SPL"]
    RAG["SOC RAG\nTSOC_VECTOR_ENABLE, QDRANT_URL\nTSOC_EMBEDDING_MODEL"]
    VT["VirusTotal\nVIRUSTOTAL_API_KEY, ENABLE"]
    Corr["Correlation\nTSOC_CORRELATION_ENABLED\nTSOC_CORRELATION_AUTO_SEED"]
  end

  subgraph frontendEnv ["frontend/.env.local"]
    Auth["Auth\nAUTH_SECRET, TSOC_DEMO_USER"]
    Proxy["Proxy\nTSOC_BACKEND_URL\nTSOC_PROXY_TIMEOUT_MS\nTSOC_PROXY_LLM_TIMEOUT_MS"]
    Public["Public\nNEXT_PUBLIC_TSOC_APP_URL"]
  end

  subgraph runtime ["Runtime Targets"]
    FastAPI["FastAPI Backend :9876"]
    NextJS["Next.js :3000"]
    Splunk["Splunk :8089"]
    Docker["Docker Compose\nPostgres / Qdrant / Neo4j"]
    LLMProvider["LLM Provider"]
    VTApi["VirusTotal API"]
  end

  HTTP --> FastAPI
  SplunkREST --> Splunk
  PG --> Docker
  Neo4j_E --> Docker
  RAG --> Docker
  LLM --> LLMProvider
  VT --> VTApi
  MCP_E --> Splunk
  SPL --> Splunk
  Ingest --> FastAPI
  Corr --> Docker

  Auth --> NextJS
  Proxy --> FastAPI
```

---

## Quick setup

```bash
# Backend
cd backend
cp .env.example .env
# Edit: SPLUNK_*, TSOC_POSTGRES_DSN, LITELLM_*, optional TSOC_INGEST_TOKEN
docker compose up -d    # postgres + qdrant (+ neo4j optional)
python run.py

# Frontend (separate terminal)
cd frontend
cp .env.example .env.local
# Edit: AUTH_SECRET, TSOC_BACKEND_URL, TSOC_INGEST_TOKEN (match backend)
npm run dev
```

**Dev layout:** PostgreSQL + Qdrant in Docker; FastAPI and Next.js on the host. Splunk is typically at `/opt/splunk` on the demo machine (`SPLUNK_MGMT_URL=https://127.0.0.1:8089`).

### After `install.sh` — integration wizard (recommended)

Instead of editing every Splunk/LiteLLM/MCP variable by hand, run the **post-install integration wizard** (offered at the end of `install.sh`):

```bash
sudo bash scripts/configure-integration.sh
```

It writes integration keys to `backend/.env` and `frontend/.env.local`, configures Splunk MCP on the instance (`scripts/setup_splunk_mcp.py`), runs a **live smoke test**, prints a masked variable summary, and reminds you to **`splunk restart`**.

- **Full guide:** [23-post-install-integration-wizard.md](./23-post-install-integration-wizard.md)  
- **Verify only:** `sudo bash install/smoke-integration-config.sh`

---


## Backend — HTTP and process

Used by `run.py` / `main.py` (not all fields are on `Settings`).

| Variable | Default | Description |
|----------|---------|-------------|
| `TSOC_HTTP_HOST` | `127.0.0.1` | Bind address for uvicorn (`python run.py`). |
| `TSOC_HTTP_PORT` | `9876` | API listen port; frontend proxies to this URL. |
| `TSOC_RELOAD` | `false` | `1` / `true` — hot-reload (development only). |
| `TSOC_RUN_NO_KILL` | `false` | If true, do not kill existing processes on `TSOC_HTTP_PORT` before bind. |
| `TSOC_RUN_SKIP_POSTGRES` | `false` | Skip auto-starting Docker Postgres in `run.py`. |
| `LOG_LEVEL` | `INFO` | Python log level for the API process. |
| `TSOC_LOG_NO_COLOR` | `false` | Disable ANSI colors in analysis-complete console output. |

---

## Backend — Splunk REST

| Variable | Default | Description |
|----------|---------|-------------|
| `SPLUNK_MGMT_URL` | `https://127.0.0.1:8089` | Splunk management URL (REST jobs, parser, AI Assistant `/predict`). |
| `SPLUNK_USERNAME` | — | Splunk REST user (required for live Splunk). |
| `SPLUNK_PASSWORD` | — | Splunk REST password. |
| `SPLUNK_VERIFY_SSL` | `false` | Verify TLS when calling Splunk REST. |
| `TSOC_SPLUNK_APP` | `search` | `servicesNS` app namespace for oneshot job results. |
| `TSOC_SPLUNK_OWNER` | `nobody` | `servicesNS` owner for REST oneshot. |
| `TSOC_SPL_PARSER_APP` | `search` | App for `POST /search/v2/parser` (must expose search REST). |

See [02-integration-boundaries.md](./02-integration-boundaries.md) for webhook and REST contracts.

---

## Backend — PostgreSQL and Neo4j

| Variable | Default | Description |
|----------|---------|-------------|
| `TSOC_POSTGRES_DSN` | — | **Required** for dashboard, ingest store, SOC chat SQL, RAG metadata, **`graph_findings`**. Example: `postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc`. |
| `NEO4J_URI` | `bolt://127.0.0.1:7687` | Neo4j Bolt URL for **Correlation** alert graph ([12-correlation-graph-service.md](./12-correlation-graph-service.md)). |
| `NEO4J_USER` | `neo4j` | Neo4j username (compose default: `neo4j`). |
| `NEO4J_PASSWORD` | `tsoc-tsoc` | Neo4j password. |
| `TSOC_CORRELATION_ENABLED` | `true` | Mount `/api/v1/graph` routes on the unified backend. |
| `TSOC_CORRELATION_AUTO_SEED` | `true` | Seed demo findings + Neo4j campaign when `graph_findings` is empty. |
| `CORRELATION_DEMO_API_KEY` | `dev-key` | `X-Demo-Api-Key` for `POST /api/v1/graph/internal/correlate`. |
| `CORRELATION_BEARER_TOKEN` | — | Optional Bearer auth on graph findings / explorer / analysis routes. |
| `SMART_ANALYSIS_LOOKBACK_DAYS` | `7` | Historical incident lookback for Smart Attack Discovery. |
| `CORRELATION_CLUSTER_WINDOW_HOURS` | `168` | Attack Discovery entity co-occurrence clustering window (hours; 168 = 7 days). |
| `CORRELATION_ANCHOR_ENTITY_PREFIXES` | — | Optional comma-separated entity **types** (no colon) treated as anchors (users, hosts, assets). Default set in `graph_core/entity_taxonomy.py`. |
| `CORRELATION_INDICATOR_ENTITY_PREFIXES` | — | Optional comma-separated types treated as IOC indicators (`ipv4`, `domain`, `sha256`, …). |

---

## Backend — Webhook ingest and routing

| Variable | Default | Description |
|----------|---------|-------------|
| `TSOC_INGEST_AUTO_ANALYZE` | `true` | After webhook enrich, run triage in background (`202` response). Not overridable via URL. |
| `TSOC_INGEST_AUTO_ANALYZE_PIPELINE` | `triage` | Pipeline when auto-analyze is on: `triage` \| `route` \| `none`. |
| `TSOC_INGEST_AUTO_ANALYZE_MAX_ROWS` | `50` | Max Splunk result rows to analyze per ingest job (sequential per-row triage; 1–500). |
| `TSOC_INGEST_ROW_BUFFER` | `true` | Buffer webhook POSTs per Splunk `sid`, then analyze the full row set once (dedupe + debounce). |
| `TSOC_INGEST_ROW_BUFFER_SECONDS` | `3.0` | Seconds after the last POST for a `sid` before flush (0.5–60). |
| `TSOC_INGEST_LOG_RAW_WEBHOOK_BODY` | `true` | Log full Splunk webhook JSON (`ingest_webhook_raw_json` + pretty multiline) to backend console. |
| `TSOC_INGEST_TOKEN` | *(empty)* | Optional shared secret for Bearer auth on ingest routes. See [TSOC_INGEST_TOKEN](#tsoc_ingest_token-optional-ingest-auth) below. |
| `TSOC_ADMIN_TOKEN` | *(empty)* | Optional admin bearer for `/integrations/settings` and other admin-only routes (`check_admin_bearer`). Separate from ingest token. |
| `TSOC_ALERT_LOG_PATH` | — | Append each enriched payload as one JSON line per file. |
| `TSOC_CLASSIFIER_LLM` | `true` | Classify alerts via LLM (full payload). |
| `TSOC_RATE_LIMIT_ENABLED` | `true` | In-process rate limit on sensitive routes (analysis, agents, integrations, soc-chat). |
| `TSOC_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit sliding window (seconds). |
| `TSOC_RATE_LIMIT_MAX_REQUESTS` | `60` | Max requests per window per client IP. |

**Security:** `RejectConfigQueryParamsMiddleware` (`backend/middleware/reject_config_query.py`) rejects requests whose query string contains env-style configuration keys (including legacy `auto_analyze` / `async_mode`). Use this section and admin integration settings only — never URL query overrides.

### TSOC_INGEST_TOKEN (optional ingest auth)

`TSOC_INGEST_TOKEN` is a **shared secret string** — not a JWT, OAuth token, or API-issued credential. The backend compares the incoming `Authorization: Bearer …` header to this value exactly. There is no separate “token mint” endpoint in ThinkingSOC Lite.

**Default:** empty / unset → ingest routes accept requests **without** a Bearer header (convenient for local demos).

**When set:** every client that calls protected ingest routes must send the same value, including Splunk and the Next.js UI proxy.

#### Where the same value must appear

| Location | File / UI |
|----------|-----------|
| Backend | `backend/.env` → `TSOC_INGEST_TOKEN=…` |
| Frontend proxy | `frontend/.env.local` → `TSOC_INGEST_TOKEN=…` (same string) |
| Splunk alert | **ThinkingSOC_Hackathon_Splunk_App** alert action → **Bearer token** field |

After changing the token, restart backend and frontend so `.env` / `.env.local` reload:

```bash
sudo systemctl restart tsoc-backend tsoc-frontend
```

#### How to create a token

**Option A — post-install wizard (recommended):**

```bash
sudo bash scripts/configure-integration.sh
```

When prompted *“Set a shared webhook ingest token (backend + frontend)?”*, answer **Yes**. The wizard generates a random value with `openssl rand -hex 24` and writes it to `backend/.env` and `frontend/.env.local`.

**Option B — manual:**

```bash
openssl rand -hex 24
```

Copy the output into `backend/.env` and `frontend/.env.local`, then paste the same string into the Splunk **ThinkingSOC_Hackathon_Splunk_App** alert action **Bearer token** field.

Any long random string is acceptable (32+ characters recommended). Do **not** commit tokens to git.

#### Behavior matrix

| Backend `TSOC_INGEST_TOKEN` | Splunk Bearer token | Result |
|---------------------------|---------------------|--------|
| Empty | Empty | ✅ Ingest accepted (default demo path) |
| Set | Empty | ❌ `401 Missing Authorization bearer token` — alert fires but nothing is stored |
| Set | Same value | ✅ Ingest accepted |
| Set | Wrong value | ❌ `403 Invalid bearer token` |

Splunk still **fires** the alert action when token auth fails; the failure appears in Splunk’s alert action logs and the backend returns an HTTP error without enrich/triage.

#### When to enable

| Scenario | Token |
|----------|-------|
| Local hackathon / lab demo | Leave empty |
| Backend reachable on LAN or internet | Set a token |

See also: [02-integration-boundaries.md](./02-integration-boundaries.md) (Splunk handoff), [ThinkingSOC_Hackathon_Splunk_App/README.md](../ThinkingSOC_Hackathon_Splunk_App/README.md) (Splunk alert action UI).

---

## Backend — LiteLLM

All SOC LLM calls (Defender, Hunter, Judge, SPL review, chat, Text-to-SQL) use **LiteLLM** ([04-agents-and-pipelines.md](./04-agents-and-pipelines.md)).

| Variable | Default | Description |
|----------|---------|-------------|
| `LITELLM_MODEL` | `gpt-4o-mini` | Model id as LiteLLM understands it. |
| `LITELLM_API_KEY` | — | **Required for AI-assisted analysis** in demos; post-install wizard always prompts for it. If unset, provider keys below may be used; otherwise pipelines use rule fallbacks. |
| `LITELLM_API_BASE` | — | Optional API base URL (e.g. NVIDIA NIM, Azure OpenAI). |
| `LITELLM_TIMEOUT_SECONDS` | `120` | HTTP timeout for LLM requests. |
| `LITELLM_RPM` | `30` | Process-wide sliding-window limit for LLM requests per minute; excess calls wait asynchronously for the next slot. |
| `LITELLM_MAX_RETRIES` | `3` | Retries after the initial attempt for transient failures only; provider-internal retries are disabled to avoid multiplying calls. |
| `LITELLM_RETRY_BASE_SECONDS` | `5` | Initial exponential-backoff delay (`5s`, `10s`, `20s` with the defaults). |
| `LITELLM_RETRY_MAX_SECONDS` | `60` | Maximum delay between retry attempts. |
| `LITELLM_MAX_TOKENS` | `131072` | Global completion token cap per request. |
| `LITELLM_CHAT_DEFAULT_TEMPERATURE` | — | Default for `POST /api/v1/llm/chat` when body omits `temperature`. |
| `OPENAI_API_KEY` | — | Provider key (LiteLLM) when `LITELLM_API_KEY` is empty. |
| `ANTHROPIC_API_KEY` | — | Provider key (LiteLLM) when `LITELLM_API_KEY` is empty. |

### SOC analysis (LangGraph)

SOC analysis (**Defender / Hunter / Judge**) always runs the LangGraph + LiteLLM path when credentials are configured. There is **no** env flag to disable LLM for the pipeline; if LiteLLM is missing or errors, stages fall back to rule-based behavior automatically.

| Variable | Default | Description |
|----------|---------|-------------|
| `TSOC_ANALYSIS_LOG_PATH` | — | Optional JSONL log of analysis records. |
| `LITELLM_ANALYSIS_MAX_TOKENS` | `8192` | Max completion tokens for structured analysis JSON. |
| `LITELLM_ANALYSIS_TEMPERATURE` | `0.2` | Temperature for analysis LLM calls. |
| `TSOC_LLM_CONTEXT_TOKENS` | `131072` | Effective context window; drives prompt truncation budgets. |
| `TSOC_SPL_ALERT_CONTEXT_MAX_CHARS` | `32768` | Max alert JSON chars in per-question SPL prompts. |
| `TSOC_SPL_COMPACT_CONTEXT` | `true` | Slim alert-only SPL context (no full analysis JSON). |
| `TSOC_INVESTIGATION_QUESTIONS_MAX` | `3` | Max follow-up investigation questions per alert (1–12). |
| `TSOC_ANALYSIS_SAIA_SPL_REVIEW` | `true` | After SPL draft: SAIA optimize + explain via MCP in Analysis UI. |

---

## Backend — VirusTotal

| Variable | Default | Description |
|----------|---------|-------------|
| `VIRUSTOTAL_API_KEY` | — | API v3 key; empty disables live lookups. |
| `VIRUSTOTAL_ENABLE` | `true` | Master switch for VT enrichment node. |
| `VIRUSTOTAL_TIMEOUT_SECONDS` | `15` | HTTP timeout per VT request. |
| `VIRUSTOTAL_BASE_URL` | `https://www.virustotal.com/api/v3` | VT API base URL. |
| `VIRUSTOTAL_MAX_IOCS` | `8` | Max IOCs queried per analysis (0–50). |

Details: [09-virustotal-threat-intel.md](./09-virustotal-threat-intel.md).

---

## Backend — Splunk MCP and SAIA

Requires Splunk **MCP Server** (Splunkbase app 7931) and optional **AI Assistant Cloud** for `/predict`.

| Variable | Default | Description |
|----------|---------|-------------|
| `TSOC_MCP_ENABLED` | `true` | Enable MCP client (execute, optional spl-generate). |
| `SPLUNK_MCP_URL` | `{SPLUNK_MGMT_URL}/services/mcp` | MCP endpoint when set; else derived from mgmt URL. |
| `SPLUNK_MCP_TOKEN` | — | Bearer token for MCP (required when MCP enabled). |
| `SPLUNK_MCP_VERIFY_SSL` | `false` | TLS verification for MCP HTTP. |
| `SPLUNK_MCP_TIMEOUT_SECONDS` | `90` | MCP HTTP timeout. |
| `TSOC_MCP_CORRELATION_ENABLED` | `false` | MCP tools for cross-alert correlation during analysis. |
| `TSOC_MCP_HUNTER_JUDGE_ENABLED` | `true` | Hunter/Judge LangGraph: live MCP hunt queries + SAIA ask before LLM reasoning. |
| `TSOC_MCP_SAIA_SPL_ONLY` | `false` | `saia_generate_spl`: SPL only vs full SAIA reply. |
| `TSOC_MCP_SAIA_OPTIMIZE_SPL` | `true` | After generate: `saia_optimize_spl`. |
| `TSOC_MCP_SAIA_EXPLAIN_SPL` | `true` | After generate: `saia_explain_spl`. |
| `TSOC_SAIA_MCP_PROMPT_MAX_CHARS` | `1000` | Max chars for MCP `prompt` (Splunk hard limit). |
| `TSOC_SAIA_LLM_PREPARE_PROMPT` | `true` | LiteLLM writes ≤1000-char prompt before MCP generate. |
| `TSOC_MCP_TRACE_LOG` | `false` | Full MCP JSON-RPC trace (`tsoc.trace.mcp`). |
| `TSOC_SAIA_TRACE_LOG` | `false` | Full SAIA trace (`tsoc.trace.saia`). |
| `TSOC_TRACE_LOG_FILE` | — | Optional file for MCP+SAIA trace lines. |
| `TSOC_SAIA_AUTO_REPAIR` | `true` | Auto-repair SAIA `cloud_connected_configurations` on startup and when `/predict` fails with configs errors. |
| `SPLUNK_HOME` | `/opt/splunk` | Splunk install path for SCS token refresh during auto-repair (`splunk cmd python3`). |

Investigation SPL flow: [13-cim-investigation-spl-mcp.md](./13-cim-investigation-spl-mcp.md).

---

## Backend — Investigation SPL

Investigation uses **`search` only** (no `tstats` / `datamodel` in the active pipeline).

| Variable | Default | Description |
|----------|---------|-------------|
| `TSOC_SPL_USE_REST_PREDICT` | `true` | Generate SPL via Splunk AI Assistant REST `/predict`. |
| `TSOC_SAIA_AUTO_REPAIR` | `true` | Auto-repair SAIA cloud-connected KV/conf when incomplete or `/predict` returns configs errors. |
| `SPLUNK_HOME` | `/opt/splunk` | Splunk install path (token refresh worker during auto-repair). |
| `TSOC_SPL_PREDICT_TIMEOUT_SECONDS` | `90` | Poll budget for async `/predict`. |
| `TSOC_SPL_PREDICT_POLL_INTERVAL_SECONDS` | `0.75` | Poll interval for `/predict`. |
| `TSOC_SPL_LLM_REVIEW` | `true` | Analysis LLM reviews/fixes SPL after predict/MCP. |
| `TSOC_SPL_LLM_REFINE_ON_ERROR` | `true` | On parser errors, pass error text to LiteLLM and re-validate. |
| `TSOC_SPL_EXECUTE_REFINE_MAX_ATTEMPTS` | `3` | Post-execute refine loops per question (0–3). |
| `TSOC_SPL_EXECUTE_VIA_MCP` | `true` | Prefer MCP `splunk_run_query`; fallback REST oneshot. |
| `TSOC_INVESTIGATION_SPL_TIME_WINDOW` | `earliest=1 latest=now` | Default Splunk time range for investigation jobs. |
| `TSOC_EXECUTE_INVESTIGATION_SPL` | `true` | `false` — generate SPL only, do not execute. |

---

## Backend — SOC vector RAG

| Variable | Default | Description |
|----------|---------|-------------|
| `TSOC_VECTOR_ENABLE` | `true` | Use Qdrant for semantic retrieval when reachable. |
| `QDRANT_URL` | `http://127.0.0.1:6333` | Qdrant HTTP API. |
| `QDRANT_COLLECTION` | `tsoc_soc_rag` | Collection name for alert/analysis embeddings. |
| `TSOC_EMBEDDING_MODEL` | `BAAI/bge-base-en-v1.5` (`bge-base`) | FastEmbed embedding model — see table below. |
| `TSOC_EMBEDDING_DIM` | `768` | Informational; runtime dim is derived from the model. |
| `TSOC_FASTEMBED_CACHE_DIR` | `/opt/.thinking-soc-cache/fastembed` | ONNX cache directory (`Settings`). |
| `FASTEMBED_CACHE_PATH` | (same) | Alias read by `embeddings.py` if `TSOC_FASTEMBED_CACHE_DIR` unset. |
| `TSOC_RAG_SIMILAR_MAX` | `3` | Similar past alerts injected into analysis (max 5). |
| `TSOC_RAG_SIMILAR_MIN_SCORE` | `0.35` | Minimum similarity score for similar alerts. |
| `TSOC_RAG_SIMILAR_LOOKBACK_DAYS` | `30` | Lookback window for similar-alert search. |
| `TSOC_RAG_SIMILAR_TOKEN_BUDGET` | `1500` | Approx token budget for similar-alert snippets in prompts. |
| `TSOC_RAG_CHAT_TOP_K` | `12` | Top-k chunks for SOC chat RAG retrieval. |
| `TSOC_RAG_BACKFILL_ON_STARTUP` | `true` | On startup, backfill Qdrant from PostgreSQL analysis rows + inventory + correlation. |

### `TSOC_EMBEDDING_MODEL` — supported values

Copy `backend/.env.example` → `backend/.env` and set **one** value. Full guide: [docs/10-soc-vector-rag.md — Embedding model selection](10-soc-vector-rag.md#embedding-model-selection).

| Value in `.env` | Also accepted | Full FastEmbed id | Download | Dim | Notes |
|-----------------|---------------|-------------------|----------|-----|-------|
| `bge-small` | `small` | `BAAI/bge-small-en-v1.5` | ~33 MB | 384 | Fastest download |
| `bge-base` | `base` | `BAAI/bge-base-en-v1.5` | ~220 MB | 768 | **Default** in `config.py` / `.env.example` |
| `bge-large` | `large` | `BAAI/bge-large-en-v1.5` | ~1.2 GB | 1024 | Best semantic match |

You may use the **full id** column instead of a preset. After a change: restart the API, then backfill if Qdrant dimension changed (`TSOC_RAG_BACKFILL_ON_STARTUP` or `POST /api/v1/soc/rag/backfill`). Check active model: `GET /api/v1/soc/chat/status` → `embedding_model`, `embedding_dim`, `embedding_model_options`.

Pre-download ONNX weights (optional, useful on slow networks):

```bash
bash scripts/download-embedding-model.sh bge-small
```

### SOC Chat — conversation persistence and session RAG

| Variable | Default | Description |
|----------|---------|-------------|
| `TSOC_CHAT_HISTORY_DIRECT_MAX` | `12` | Send full message history verbatim to the LLM when turn count ≤ this value. |
| `TSOC_CHAT_HISTORY_RAG_TOP_K` | `8` | When history is longer, retrieve this many prior session turns from RAG. |
| `TSOC_CHAT_HISTORY_RECENT_TAIL` | `4` | Always include the last N turns alongside session-RAG hits. |

Details: [10-soc-vector-rag.md](./10-soc-vector-rag.md#session-rag-long-conversations).

---

## Backend — SOC chat Text-to-SQL

| Variable | Default | Description |
|----------|---------|-------------|
| `TSOC_CHAT_SQL_ENABLE` | `true` | Route statistical questions to Text-to-SQL. |
| `TSOC_CHAT_SQL_MAX_ROWS` | `500` | Max rows returned from generated SQL. |
| `TSOC_CHAT_SQL_TIMEOUT_SECONDS` | `5` | SQL execution timeout. |
| `TSOC_CHAT_SQL_MAX_TOKENS` | `131072` | Max tokens for SQL-generation LLM. |
| `TSOC_CHAT_SQL_CLASSIFY_MAX_TOKENS` | `2560` | Max tokens for statistical vs narrative classifier. |
| `TSOC_CHAT_SQL_ANSWER_MAX_TOKENS` | `2048` | Max tokens for NL answer over large result sets. |
| `TSOC_CHAT_SQL_MODEL` | — | Optional separate model for SQL gen (non-thinking instruct recommended). |

**Allowed SQL tables** (whitelist in `sql_schema.py`): `tsoc_records`, `tsoc_rag_documents`, `tsoc_users`, `tsoc_assets`, `tsoc_relationships`, **`graph_findings`** (Correlation findings — use for “highest risk correlation findings”, not `tsoc_records` `soc_analysis`).

---

## Backend — Live Splunk tests (dev/CI only)

| Variable | Default | Description |
|----------|---------|-------------|
| `TSOC_RUN_SPLUNK_LIVE` | — | Set `1` to enable pytest live Splunk tests. |
| `TSOC_LIVE_API_BASE` | `http://127.0.0.1:9876` | Base URL for live API tests. |
| `TSOC_LIVE_SKIP_METADATA` | — | Set `1` to skip optional metadata live test. |

Notes:
- Default `pytest` runs are **fast/deterministic** and do **not** perform external startup (Splunk login, embeddings/RAG warmup, correlation startup).
- Use `pytest -m real_startup -v -s` to opt into real FastAPI lifespan startup during tests.

---

## Frontend — Next.js

Copy [`frontend/.env.example`](../frontend/.env.example) to `frontend/.env.local`.

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_SECRET` | (dev fallback) | Session signing secret — **change in production**. |
| `TSOC_DEMO_USER` | `admin` | Demo login username (hackathon UI). |
| `TSOC_DEMO_PASSWORD` | — | Demo login password. |
| `TSOC_BACKEND_URL` | `http://127.0.0.1:9876` | Server-side proxy target (Next.js → FastAPI). |
| `TSOC_INGEST_TOKEN` | *(empty)* | Must **match** `backend/.env` when ingest protection is enabled. See [TSOC_INGEST_TOKEN](./11-environment-configuration.md#tsoc_ingest_token-optional-ingest-auth). |
| `TSOC_PROXY_TIMEOUT_MS` | `300000` | Undici timeout (ms) for ordinary `/api/backend/*` requests. |
| `TSOC_PROXY_LLM_TIMEOUT_MS` | `900000` | Timeout for LLM-heavy POST routes, allowing slow providers and bounded retries to finish. |
| `TSOC_PROXY_CHAT_TIMEOUT_MS` | — | Legacy fallback name used only when `TSOC_PROXY_LLM_TIMEOUT_MS` is unset. |
| `TSOC_DEV_ORIGIN` | `127.0.0.1,localhost` | Comma-separated browser hosts for Next dev HMR / CORS. |
| `NEXT_PUBLIC_TSOC_APP_URL` | — | Public UI URL hint (shown in UI; no secrets). |
| `NEXT_PUBLIC_TSOC_SPLUNK_HOST` | — | Splunk host hint for UI links. |
| `NEXT_PUBLIC_TSOC_SPLUNK_PORT` | `8089` | Splunk mgmt port hint for UI links. |

`NEXT_PUBLIC_*` values are exposed to the browser; never put API keys there.

---

## Removed or unused variables

Do **not** set these; they are not read by the current codebase:

| Variable | Notes |
|----------|--------|
| `TSOC_MCP_PREFER_SAIA_SPL` | Removed; use `TSOC_SPL_USE_REST_PREDICT`. |
| `TSOC_CIM_*` | CIM/datamodel schema env vars removed — investigation uses `search` only. |
| `TSOC_CIM_SPL_ENABLED`, `TSOC_CIM_TSTATS_DEFAULT_TIME_WINDOW` | Legacy; unused. |
| `TSOC_SAIA_PATCH_*`, `SPLUNK_SAIA_APP_PATH` | Internal/dev only; not in `Settings`. |

Legacy `tsoc_cim_*` fields may still exist in `config.py` for backward compatibility but are **not** documented in `.env.example` and are **not** wired into the investigation pipeline.

---

## Related documents

| Topic | Document |
|-------|----------|
| Agents and LiteLLM | [04-agents-and-pipelines.md](./04-agents-and-pipelines.md) |
| Splunk contracts | [02-integration-boundaries.md](./02-integration-boundaries.md) |
| Investigation SPL | [13-cim-investigation-spl-mcp.md](./13-cim-investigation-spl-mcp.md) |
| Vector RAG | [10-soc-vector-rag.md](./10-soc-vector-rag.md) |
| VirusTotal | [09-virustotal-threat-intel.md](./09-virustotal-threat-intel.md) |
| Run API locally | [backend/README.md](../backend/README.md) |
