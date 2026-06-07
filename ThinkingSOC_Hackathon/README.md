# Splunk app: `ThinkingSOC_Hackathon`

**Splunk version:** developed and expected to run on **Splunk 10+** (Enterprise or Cloud).

This app is intentionally minimal for the hackathon:

- index definition (`thinking_soc`) for Splunk-side data/search use
- **no** CSV lookups (inventory lives in PostgreSQL)
- custom modular alert action **ThinkingSOC_Hackathon** (replaces generic Webhook in the UI)

Install path:

`$SPLUNK_HOME/etc/apps/ThinkingSOC_Hackathon/`

After installing/reloading the app, configure each alert:

1. **Trigger Actions → Add Actions → ThinkingSOC_Hackathon**
2. **Backend URL:** `http://127.0.0.1:9876/api/v1/alerts/splunk-ingest` (or your backend host)
3. **Bearer token:** see [Ingest token](#ingest-token-tsoc_ingest_token) below

Webhook payload from Splunk includes `sid` and **only the first** result row under `result` (see `bin/thinkingsoc_hackathon.py`). The backend logs that object (`ingest_webhook_payload`) and, when `SPLUNK_USERNAME` / `SPLUNK_PASSWORD` are set in `backend/.env`, **fetches all job rows via Splunk REST** by `sid` — required for multi-row searches (e.g. `| head 2`).

## Auto ingestion (default)

After `install.sh`, `backend/.env` includes **`TSOC_INGEST_AUTO_ANALYZE=true`**. Each alert triggers background triage (HTTP **202**). To ingest-only without analysis, set `TSOC_INGEST_AUTO_ANALYZE=false` in `backend/.env` and restart the backend.

**Do not** append query parameters to the backend URL (e.g. `?auto_analyze=true`). The API rejects config-style query keys with HTTP **400**. See [docs/02-integration-boundaries.md](../docs/02-integration-boundaries.md).

## Ingest token (`TSOC_INGEST_TOKEN`)

Optional shared secret between Splunk and the ThinkingSOC backend. **Not** a Splunk or OAuth token — you choose a random string (or let the install wizard generate one).

### Default (no token)

If `TSOC_INGEST_TOKEN` is **empty** in `backend/.env`:

- Leave the Splunk alert action **Bearer token** field empty
- Ingest works without authentication (typical for local demos)

### When backend token is set

You **must** paste the **same** value into the Splunk **Bearer token** field. Otherwise the backend returns `401` and **no data is ingested** (the alert still fires in Splunk).

Also set the same value in `frontend/.env.local` so the UI proxy can call the backend.

### How to create a token

**Wizard:**

```bash
sudo bash scripts/configure-integration.sh
```

Answer **Yes** to *“Set a shared webhook ingest token?”* — generates `openssl rand -hex 24` and writes `backend/.env` + `frontend/.env.local`.

**Manual:**

```bash
openssl rand -hex 24
```

Add to `backend/.env`:

```bash
TSOC_INGEST_TOKEN=<paste-generated-value>
```

Mirror in `frontend/.env.local`, then restart:

```bash
sudo systemctl restart tsoc-backend tsoc-frontend
```

Copy the same string into Splunk: alert → **Trigger Actions** → **ThinkingSOC_Hackathon** → **Bearer token**.

### Quick reference

| Backend token | Splunk Bearer | Result |
|---------------|---------------|--------|
| Empty | Empty | ✅ Works |
| Set | Empty | ❌ 401 — nothing ingested |
| Set | Same value | ✅ Works |
| Set | Wrong value | ❌ 403 |

Full documentation: [docs/11-environment-configuration.md](../docs/11-environment-configuration.md#tsoc_ingest_token-optional-ingest-auth).

## Index `thinking_soc`

This app defines **`default/indexes.conf`** with index **`thinking_soc`**.

Backend analysis/audit storage and **inventory** (users, assets, relationships) are in **PostgreSQL** (`TSOC_POSTGRES_DSN`). Demo inventory CSVs ship under `backend/data/demo/` and are seeded on first setup.
