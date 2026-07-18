# backend/data

Demo data and configuration used by the ThinkingSOC Lite backend.

## Key files

| Path | Purpose |
|------|---------|
| `integration_settings.json` | LiteLLM and integration override settings (API keys, hidden builtins) |
| `demo/` | Demo inventory CSVs loaded into PostgreSQL on first startup |
| `demo/tsoc_users.csv` | Default sample users |
| `demo/tsoc_assets.csv` | Default sample assets |
| `demo/tsoc_relationships.csv` | Default user–asset relationships |
| `demo/attacks_t8372/` | ATTACKS campaign demo data (users, assets, relationships, enriched webhooks) |
| `demo/botsv1_osk_sysmon/` | BOTSv1 osk.exe Sysmon scenario inventory data |
| `demo/observability_cpu_latency/` | Observability CPU/latency scenario inventory data |

Each `demo/` subdirectory contains `tsoc_users.csv`, `tsoc_assets.csv`, and `tsoc_relationships.csv` for its scenario.

## Related docs

- [docs/14-inventory-service.md](../../docs/14-inventory-service.md)
- [docs/24-demo-postgresql-data.md](../../docs/24-demo-postgresql-data.md)
