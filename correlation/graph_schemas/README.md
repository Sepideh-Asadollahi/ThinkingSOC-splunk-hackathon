# graph_schemas

Pydantic models for the Graph Correlation API request/response contracts.

## Key files

| File | Description |
|------|-------------|
| `analysis.py` | Request/response models for attack discovery and async operation status tracking |
| `exploration.py` | Graph topology models — nodes, edges, highlights, attack trees, and correlate request/response |
| `finding.py` | Finding models — summary, details, paginated list response, and ticket patch request |

## Related docs

- [Correlation Graph Service](../../docs/12-correlation-graph-service.md)
- [Database Schema](../../docs/21-database-schema.md)
