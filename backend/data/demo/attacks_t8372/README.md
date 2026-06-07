# Demo data — ATTACKS campaign t8372

| Path | Role |
|------|------|
| `tsoc_users.csv` | Inventory users (Postgres) |
| `tsoc_assets.csv` | Inventory assets |
| `tsoc_relationships.csv` | User–asset relationships |
| `enriched_webhooks/` | Optional: `enrich_attacks_correlation.py --write-enriched` |

Splunk-only events: `scripts/samples/ATTACKS/attack_step_*.json`.

Graph entities (host, user, public IPs) are extracted from each alert’s `result` row. Campaign linking and incidents are produced by **Attack Discovery**, not by seed Cypher.
