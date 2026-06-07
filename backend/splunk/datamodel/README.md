# backend/splunk/datamodel

Splunk CIM (Common Information Model) data model discovery and schema helpers.

## Key files

| File | Purpose |
|------|---------|
| `cim_schema.py` | Discover CIM data model structure via `\| datamodelsimple`, build prompt-ready schema summaries, and infer the primary data model for an alert |
| `__init__.py` | Re-exports `CimDatamodelCatalog`, `CimDatamodelSchema`, `fetch_cim_datamodel_catalog`, `fetch_cim_datamodel_schema`, `build_cim_schema_summary_for_prompt`, `infer_cim_datamodel` |

## Related docs

- [docs/13-cim-investigation-spl-mcp.md](../../../docs/13-cim-investigation-spl-mcp.md)
