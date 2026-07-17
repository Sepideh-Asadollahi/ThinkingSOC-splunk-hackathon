# backend/scripts

Utility scripts for the ThinkingSOC backend. Requires `backend/.venv` and a running PostgreSQL instance.

## Contents

| File | Purpose |
|------|---------|
| `spl_predict_ask.py` | Query Splunk AI Assistant via REST `/predict` and execute SPL via MCP |
| `seed/` | Demo inventory seeding and enrichment scripts (see `seed/` README) |

## seed/

| File | Purpose |
|------|---------|
| `export_demo_postgres_snapshot.py` | Export live PostgreSQL demo snapshot (`postgres_snapshot/` + manifest) |
| `enrich_attacks_correlation.py` | Build enriched webhook payloads for the ATTACKS demo (inventory + graph correlation) |
| `enrich_botsv1_sample.py` | Seed BOTSv1 inventory and enrich the BOTSv1 Sysmon webhook sample |
| `seed_botsv1_osk_inventory.py` | Seed PostgreSQL inventory for the BOTSv1 osk.exe Sysmon scenario |
| `seed_observability_cpu_latency_inventory.py` | Seed PostgreSQL inventory for the observability CPU/latency scenario |
| `seed_runbook_judge_demo.py` | Idempotently add the complete synthetic Runbook judge tour and backfill its Chat/RAG documents; never removes existing demo rows |

## Related docs

- [docs/07-lld-low-level-design.md](../../docs/07-lld-low-level-design.md)
