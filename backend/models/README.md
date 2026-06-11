# backend/models

Parent: [README.md](../README.md)

Pydantic request/response and domain contracts.

## Contents

| Module | Contracts |
|--------|-----------|
| `handoff.py` | Splunk webhook ingest shapes |
| `agentic_ops.py` | Alert classification and routing |
| `analysis.py` | SOC analysis request/response |
| `observability.py` | Observability pipeline contracts |
| `enrichment.py` | Inventory enrichment resolution |
| `inventory.py` | Users, assets, relationships CRUD |
| `triage.py` | Triage queue and priority |
| `agents.py` | Agent triage orchestration |
| `assistant.py` | SPL suggest / investigation assistant |
| `mcp.py` | Splunk MCP tool contracts |
| `admin_org.py` | Admin org GAP question |
| `dashboard.py` | Dashboard overview KPIs |
| `integration_settings.py` | Splunk connection UI settings |

## See also

- [README.md](../README.md)
- [07-lld-low-level-design.md](../../docs/07-lld-low-level-design.md)
