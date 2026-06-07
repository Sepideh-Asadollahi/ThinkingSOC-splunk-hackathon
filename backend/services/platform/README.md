# Platform Service

Platform-level services for the dashboard UI. Aggregates KPIs and activity timelines from PostgreSQL, manages integration settings for the Splunk connection, and collects host OS resource metrics.

## Key files

| File | Description |
|------|-------------|
| `dashboard_overview.py` | Builds dashboard overview from PostgreSQL stats and triage queue |
| `integration_settings.py` | Persists and lists integration settings for the Splunk connection UI |
| `system_resources.py` | Host OS CPU and memory metrics via psutil |

## Related docs

- [Dashboard](../../../docs/16-dashboard.md)
