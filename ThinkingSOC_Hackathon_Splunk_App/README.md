# Splunk app: `ThinkingSOC_Hackathon_Splunk_App`

**Splunk version:** developed and expected to run on **Splunk 10+** (Enterprise or Cloud).

This app is intentionally minimal for the hackathon:

- index definition (`thinking_soc`) for Splunk-side data/search use
- **no** active CSV lookups (inventory lives in PostgreSQL; `metadata/default.meta` may still list legacy `tsoc_identity_rules` transforms — unused by the backend)
- custom modular alert action **ThinkingSOC_Hackathon_Splunk_App** (replaces generic Webhook in the UI)

Install path:

`$SPLUNK_HOME/etc/apps/ThinkingSOC_Hackathon_Splunk_App/`

After installing/reloading the app, configure each alert:

1. **Trigger Actions → Add Actions → ThinkingSOC_Hackathon_Splunk_App**
2. **Backend URL:** `http://127.0.0.1:9876/api/v1/alerts/splunk-ingest` (or your backend host)
3. **Bearer token:** see [Ingest token](#ingest-token-tsoc_ingest_token) below

## Webhook payload (multi-row aware)

`bin/thinkingsoc_hackathon.py` posts JSON to the backend:

| Field | Always | Role |
|-------|--------|------|
| `sid` | Yes | Splunk search job ID |
| `search_name` | Yes | Saved search / alert name |
| `result` | Yes | First result row (backward compatible) |
| `results` | When job has 2+ rows | All rows read from Splunk’s `results.csv.gz` |

Splunk passes `results_file=/opt/splunk/var/run/splunk/dispatch/{sid}/results.csv.gz` on stdin settings. The script **decompresses gzip** and parses CSV — do not read that path as plain UTF-8 text.

**Backend behavior** (see [docs/02-integration-boundaries.md](../docs/02-integration-boundaries.md)):

1. Accept `result` and/or `results[]`.
2. Buffer rows per `sid` (default 3s debounce).
3. Confirm row count via Splunk REST when credentials are set.
4. Analyze each row separately; storage sids `…-1`, `…-2`, … for multi-row jobs.

With `alert.digest_mode=true` (common), Splunk invokes the action **once** and the app sends **all rows in one HTTP POST**. With `digest_mode=false`, Splunk may invoke once per row; the backend buffer still merges them before triage.

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

Copy the same string into Splunk: alert → **Trigger Actions** → **ThinkingSOC_Hackathon_Splunk_App** → **Bearer token**.

### Quick reference

| Backend token | Splunk Bearer | Result |
|---------------|---------------|--------|
| Empty | Empty | ✅ Works |
| Set | Empty | ❌ 401 — nothing ingested |
| Set | Same value | ✅ Works |
| Set | Wrong value | ❌ 403 |

Full documentation: [docs/11-environment-configuration.md](../docs/11-environment-configuration.md#tsoc_ingest_token-optional-ingest-auth).

## Troubleshooting (splunkd.log)

| Log | Meaning |
|-----|---------|
| `Loaded N result row(s) from results_file=…results.csv.gz` | Gzip CSV read OK |
| `Outgoing ThinkingSOC webhook rows=N` | N rows in one POST |
| `Webhook receiver responded with HTTP status=202` | Backend accepted (buffered / auto-analyze) |
| `utf-8 codec can't decode byte 0x8b` | **Fixed:** old script read `.gz` as plain text — redeploy `bin/thinkingsoc_hackathon.py` |

## Index `thinking_soc`

This app defines **`default/indexes.conf`** with index **`thinking_soc`**.

Backend analysis/audit storage and **inventory** (users, assets, relationships) are in **PostgreSQL** (`TSOC_POSTGRES_DSN`). Demo inventory CSVs ship under `backend/data/demo/` and are seeded on first setup.
