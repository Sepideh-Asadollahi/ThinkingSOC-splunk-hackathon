# ATTACKS — Splunk webhook payloads only (t8372)

Four-step kill chain on **DESKTOP-BRUCE** / **WAYNECORPINC\\bwayne**. These files mimic what **Splunk’s built-in webhook** sends — nothing else.

## What belongs here

| Field | Purpose |
|-------|---------|
| `sid` | Splunk search job ID |
| `search_name` | Saved search / alert name |
| `app`, `owner`, `server_uri`, `results_link` | Splunk context |
| `result` | First triggered row (raw event fields: host, user, IPs, severity, …) |

Each step includes at least one **VirusTotal-testable** CIM field (`url`, `domain`, `sha256`, or a **public** `remote_ip`). RFC 5737 TEST-NET IPs (`203.0.113.x`, `198.51.100.x`) stay for correlation/graph demos but are **not** sent to VT.

| Step | VT IOC field(s) | Type |
|------|-----------------|------|
| 1 phishing | `url`, `domain` | URL / domain |
| 2 PowerShell | `url`, `domain` | URL / domain |
| 3 persistence | `sha256` (EICAR test file) | file hash |
| 4 C2 | `domain`, `remote_ip` (`1.1.1.1`) | domain + public IP |

## What does **not** belong here

| Field | Where it comes from |
|-------|---------------------|
| `normalized` | Backend on ingest (`normalize_splunk_ingest_payload`) |
| `enrichment` | Inventory match (`data/demo/attacks_t8372/*.csv`) |
| `correlation` | Derived from alert fields + inventory (`services/alert/graph_correlation.py`) |

No hardcoded Neo4j Cypher for this campaign. **Attack Discovery** + LLM merge clusters; `incident_sync` links alerts after a finding is created.

## Enrich + ingest

```bash
cd backend
source .venv/bin/activate

python scripts/seed/enrich_attacks_correlation.py --seed-inventory --verify
python scripts/seed/enrich_attacks_correlation.py --write-enriched --verify   # optional lab payloads

# Raw ATTACKS or enriched — both upsert graph entities on ingest
python3 ../scripts/test_splunk_webhook.py scripts/samples/ATTACKS/attack_step_1_phishing.json --mode webhook

# Neo4j: upsert from alert fields only (no CAUSED / PART_OF_INCIDENT seed)
python scripts/seed/enrich_attacks_correlation.py --seed-neo4j
```
