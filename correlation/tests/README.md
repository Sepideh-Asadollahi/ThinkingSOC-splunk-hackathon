# tests

Pytest-asyncio test suite for the graph correlation service. Tests run against the backend ASGI app with seeded Neo4j and PostgreSQL databases.

## Key files

| File | Description |
|------|-------------|
| `conftest.py` | Shared fixtures — loads backend app, seeds databases, provides async `httpx` test client |
| `test_correlate.py` | Internal `/correlate` endpoint — verifies entity-based alert correlation |
| `test_attack_alert_filter.py` | Unit tests for attack-indicative filtering, entity clustering, enrichment, and scoring |
| `test_alert_centric_topology.py` | Tests for CAUSED-edge dedup and alert-centric attack tree construction |
| `test_findings_topology.py` | Integration tests for findings list, topology graph-data, and finding detail endpoints |
| `test_incident_sync.py` | Unit tests for Neo4j incident sync and CAUSED chain creation (mocked driver) |
| `test_cluster_merge.py` | Tests for heuristic cluster merge, partition logic, and alert merging |
| `test_entity_taxonomy.py` | Entity prefix classification and indicator split merge guard (generic IDs) |
| `test_load_alerts_campaign_expand.py` | Neo4j load expand/cap with `limit` (integration) |
| `test_discover_flow.py` | End-to-end test for the `/discover-attack-paths` async pipeline |
| `test_ticket_and_history.py` | Tests for ticket patching (status, notes) and historical incident lookup |

## Related docs

- [Correlation Graph Service](../../docs/12-correlation-graph-service.md)
