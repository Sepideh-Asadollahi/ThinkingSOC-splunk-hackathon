"""PostgreSQL schema context for SOC Chat Text-to-SQL."""

from __future__ import annotations

from .sql_chat.soc_user_intent import SOC_USER_VOCABULARY

# Tables the LLM may reference (validated at runtime).
ALLOWED_SQL_TABLES: frozenset[str] = frozenset(
    {
        "tsoc_records",
        "tsoc_rag_documents",
        "tsoc_users",
        "tsoc_assets",
        "tsoc_relationships",
        "graph_findings",
    }
)

TABLE_SELECTION_GUIDE = """
## How to pick the right table (read this first)

The analyst does NOT know table names. They say "alerts in SOC" meaning what they see on the **Analysis page** (/analysis).

{user_vocab}

| User intent (examples) | Use this table | Key filter |
|------------------------|----------------|------------|
| "how many alerts in SOC", "alerts available", "list alerts" (vague) | tsoc_records | tsoc_record_type IN ('soc_analysis','observability_analysis') — same as /api/v1/triage/queue |
| Security track / security alerts only | tsoc_records | tsoc_record_type = 'soc_analysis' |
| Observability track | tsoc_records | tsoc_record_type = 'observability_analysis' |
| Indexed Splunk alerts / RAG / vector index (explicit) | tsoc_rag_documents | doc_type = 'splunk_alert' |
| SOC analysis in RAG index | tsoc_rag_documents | doc_type = 'soc_analysis' |
| All ingested Splunk rows / raw ingest | tsoc_records | tsoc_record_type = 'splunk_ingest' |
| CMDB users / assets / relationships | tsoc_users, tsoc_assets, tsoc_relationships | — |
| Correlation findings / attack discovery / graph findings | graph_findings | risk_score, finding_type, display_id |
| Correlation indexed in chat RAG | tsoc_rag_documents | doc_type IN ('correlation_finding','correlation_alert','correlation_attack_path') |

**Default for vague "alerts in SOC":** `tsoc_records` (Analysis queue), NOT `splunk_alert` unless they say indexed/RAG.

**Correlation findings (highest risk, list findings):** `graph_findings` — NOT `tsoc_records` soc_analysis.

**List + count:** one query with `COUNT(*) OVER ()` plus row columns, or COUNT only if they only ask "how many".
""".format(user_vocab=SOC_USER_VOCABULARY).strip()

SOC_SQL_SCHEMA_PROMPT = """
PostgreSQL schema for ThinkingSOC Lite (read-only SELECT only).

{table_guide}

---

## Table: tsoc_rag_documents

**Purpose:** Searchable index for SOC Chat vector RAG (retrieval). NOT the same as the Analysis page queue.

**Columns:**
- doc_id (TEXT, PK) — unique document id
- doc_type (TEXT) — discriminates document kind (see values below)
- sid (TEXT, nullable) — Splunk search id when applicable
- search_name (TEXT, nullable) — Splunk saved search / alert name
- row_index (INT) — row offset within a Splunk result set
- essential (JSONB) — compact fields (e.g. severity, entities, host, user)
- summary_line (TEXT) — one-line human summary for UI and chat
- chunk_text (TEXT) — full text chunk used for embedding / retrieval
- metadata (JSONB) — extra structured fields
- created_at, updated_at (TIMESTAMPTZ)

**doc_type values (use in WHERE):**
- `splunk_alert` — indexed Splunk alert (only when user says indexed/RAG)
- `soc_analysis` — SOC security analysis (Defender/Hunter/Judge pipeline output)
- `observability_analysis` — observability pipeline output
- `inventory_user` — user row from asset inventory
- `inventory_asset` — asset row from asset inventory
- `inventory_relationship` — user–asset relationship row
- `correlation_finding` — graph correlation attack-discovery finding (also in graph_findings table)
- `correlation_alert` — Neo4j alert node linked in correlation graph
- `correlation_attack_path` — CAUSED edge between correlated alerts

**Risk on correlation findings in RAG:** `(essential->>'risk_score')::int` or metadata finding_id

**Severity on alerts:** `LOWER(essential->>'severity')` — critical, high, medium, low, informational

**When to use:** Count/list/breakdown of *indexed* items visible to SOC Chat; "how many alerts"; severity breakdowns on indexed alerts.

**When NOT to use:** Raw ingest volume or events not yet indexed — use tsoc_records instead.

---

## Table: tsoc_records

**Purpose:** Append-only store of *all* TSOC events. **Analysis page** lists analyses here (soc_analysis + observability_analysis).

**Columns:**
- id (BIGSERIAL, PK)
- created_at (TIMESTAMPTZ)
- tsoc_record_type (TEXT) — event kind (see below)
- sid, search_name, row_index (nullable, same meaning as RAG)
- payload (JSONB) — full event body

**tsoc_record_type values (use in WHERE):**
- `splunk_ingest` — ingested Splunk alert row (use for "all ingested alerts")
- `soc_analysis`, `soc_analysis_audit`, `soc_analysis_batch` — security analysis (Analysis → Security)
- `observability_analysis` — observability analysis (Analysis → Observability)

**Severity on ingest (splunk_ingest only):** `LOWER(payload->'normalized'->>'severity')` — often empty on soc_analysis rows.

**Investigation priority (Analysis page — UI column `priority=`):**
`LOWER(COALESCE(payload->'analysis'->'triage'->>'investigation_priority', payload->'triage'->>'investigation_priority'))`
Values: critical, high, medium, low. Triage score when present:
`(payload->'analysis'->'triage'->>'triage_score')::int`
Do **not** use `payload->'normalized'->>'severity'` for "high alerts" on soc_analysis — that is Splunk ingest severity and is often NULL on analyses.
When filtering by priority, include `payload` in SELECT (or id + search_name) so results can be interpreted.

**When to use:** Total rows in storage; timelines; "everything ingested"; comparisons not limited to the RAG index.

**When to use for "alerts in SOC":** Count/list analyses visible on /analysis — filter tsoc_record_type IN ('soc_analysis','observability_analysis').

**When NOT to use:** User explicitly asks for *indexed/RAG* Splunk alerts — then tsoc_rag_documents.

---

## Table: tsoc_users

**Purpose:** CMDB / inventory users (not Splunk alerts).

**Columns:** user_id (PK), display_name, email, department, risk_score, description, updated_at

**When to use:** "how many users", user inventory counts/lists.

---

## Table: tsoc_assets

**Purpose:** CMDB / inventory assets (hosts, servers, etc.).

**Columns:** asset_id (PK), asset_type, hostname, fqdn, ip, owner, criticality, risk_score, description, updated_at

**When to use:** "how many assets", asset inventory counts/lists.

---

## Table: tsoc_relationships

**Purpose:** Links users to assets in inventory.

**Columns:** relationship_id (PK), user_id, asset_id, description, updated_at

**When to use:** relationship counts or lists between users and assets.

---

## Table: graph_findings

**Purpose:** Graph **Correlation** service findings (attack discovery clusters). Same data as Correlation UI (/correlation). NOT the Analysis page queue.

**Columns:**
- id (UUID, PK)
- display_id (VARCHAR) — human-readable id e.g. FIND-001
- finding_type (VARCHAR) — e.g. `smart_attack_discovery`
- title (TEXT), summary (TEXT)
- details (JSONB) — incident_id, contributing_alerts, key_entities, attack_analysis_steps, etc.
- risk_score (INTEGER) — **use this for "highest risk" correlation questions**
- status, ticket_status, owner (VARCHAR)
- agent_validation_status (VARCHAR, nullable)
- created_at, updated_at (TIMESTAMPTZ)

**When to use:** "correlation findings", "attack discovery", "highest risk findings", count/list findings from graph correlation.

**When NOT to use:** Generic SOC analysis queue → tsoc_records. Splunk alert severity → tsoc_rag_documents splunk_alert.

**Example — top findings by risk:**
SELECT display_id, title, summary, risk_score, finding_type, ticket_status
FROM graph_findings
ORDER BY risk_score DESC
LIMIT 10

---

## SQL rules

- PostgreSQL syntax only. SELECT only. No semicolons. No SQL comments.
- Use only the six tables above.
- Cast counts: `COUNT(*)::int AS cnt`
- Case-insensitive text: `LOWER(...) = 'high'`
- Time windows: `created_at >= NOW() - INTERVAL '7 days'`
- Always set `tables_used` in JSON to the primary table(s) you query.

## Example queries

-- Alerts on Analysis page (default for "how many alerts in SOC")
SELECT COUNT(*)::int AS cnt
FROM tsoc_records
WHERE tsoc_record_type IN ('soc_analysis', 'observability_analysis');

-- Count + list Analysis queue (same as /analysis UI)
SELECT COUNT(*) OVER ()::int AS total_count,
       search_name, sid, tsoc_record_type, created_at
FROM tsoc_records
WHERE tsoc_record_type IN ('soc_analysis', 'observability_analysis')
ORDER BY created_at DESC;

-- Analysis items with high investigation priority (NOT normalized.severity)
SELECT search_name, sid, tsoc_record_type,
       LOWER(COALESCE(payload->'analysis'->'triage'->>'investigation_priority',
                      payload->'triage'->>'investigation_priority')) AS investigation_priority,
       (payload->'analysis'->'triage'->>'triage_score')::int AS triage_score
FROM tsoc_records
WHERE tsoc_record_type IN ('soc_analysis', 'observability_analysis')
  AND LOWER(COALESCE(payload->'analysis'->'triage'->>'investigation_priority',
                     payload->'triage'->>'investigation_priority')) = 'high'
ORDER BY created_at DESC;

-- Indexed Splunk alerts in RAG (only when user says indexed/RAG)
SELECT COUNT(*)::int AS cnt
FROM tsoc_rag_documents
WHERE doc_type = 'splunk_alert';

-- Alerts by severity (indexed)
SELECT LOWER(essential->>'severity') AS severity, COUNT(*)::int AS cnt
FROM tsoc_rag_documents
WHERE doc_type = 'splunk_alert'
GROUP BY 1 ORDER BY cnt DESC;

-- All ingested Splunk rows in storage (not the same as RAG index count)
SELECT COUNT(*)::int AS cnt
FROM tsoc_records
WHERE tsoc_record_type = 'splunk_ingest';

-- Inventory
SELECT COUNT(*)::int AS cnt FROM tsoc_users;
SELECT COUNT(*)::int AS cnt FROM tsoc_assets;

-- Correlation findings (highest risk)
SELECT display_id, title, risk_score, finding_type, ticket_status
FROM graph_findings
ORDER BY risk_score DESC
LIMIT 10;
""".format(table_guide=TABLE_SELECTION_GUIDE).strip()
