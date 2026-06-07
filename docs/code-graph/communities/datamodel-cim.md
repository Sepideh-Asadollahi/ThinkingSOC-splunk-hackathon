# datamodel-cim

## Overview

Community of 23 nodes

- **Size**: 23 nodes
- **Cohesion**: 0.2629
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| CimObjectInfo | Class | backend/splunk/datamodel/cim_schema.py | 26-28 |
| CimDatamodelCatalog | Class | backend/splunk/datamodel/cim_schema.py | 32-48 |
| summary_for_prompt | Function | backend/splunk/datamodel/cim_schema.py | 37-48 |
| CimDatamodelSchema | Class | backend/splunk/datamodel/cim_schema.py | 52-145 |
| root_object | Function | backend/splunk/datamodel/cim_schema.py | 57-61 |
| object_for_nodename | Function | backend/splunk/datamodel/cim_schema.py | 63-68 |
| field_prefix_for_nodename | Function | backend/splunk/datamodel/cim_schema.py | 70-77 |
| attribute_names | Function | backend/splunk/datamodel/cim_schema.py | 79-98 |
| prefixed_field | Function | backend/splunk/datamodel/cim_schema.py | 100-127 |
| schema_summary_for_prompt | Function | backend/splunk/datamodel/cim_schema.py | 129-145 |
| _attr_key | Function | backend/splunk/datamodel/cim_schema.py | 173-178 |
| _merge_attributes | Function | backend/splunk/datamodel/cim_schema.py | 181-188 |
| _run_datamodelsimple | Function | backend/splunk/datamodel/cim_schema.py | 191-203 |
| _fetch_attributes_for_object | Function | backend/splunk/datamodel/cim_schema.py | 206-237 |
| _parse_model_name_from_row | Function | backend/splunk/datamodel/cim_schema.py | 240-245 |
| fetch_cim_datamodel_catalog | Function | backend/splunk/datamodel/cim_schema.py | 248-298 |
| schema_summary_limits | Function | backend/splunk/datamodel/cim_schema.py | 301-315 |
| build_cim_schema_summary_for_prompt | Function | backend/splunk/datamodel/cim_schema.py | 318-350 |
| fetch_cim_datamodel_schema | Function | backend/splunk/datamodel/cim_schema.py | 353-460 |
| test_parse_model_name_from_row | Test | backend/tests/test_cim_datamodel_catalog.py | 12-15 |
| test_catalog_summary_lists_all_models | Test | backend/tests/test_cim_datamodel_catalog.py | 18-25 |
| test_build_cim_schema_summary_combines_catalog_and_schema | Test | backend/tests/test_cim_datamodel_catalog.py | 28-54 |
| test_b1_cim_datamodel_schema | Test | backend/tests/test_splunk_live_mcp_saia.py | 149-153 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `get` (20 edge(s))
- `append` (14 edge(s))
- `format` (14 edge(s))
- `len` (9 edge(s))
- `str` (8 edge(s))
- `info` (8 edge(s))
- `strip` (6 edge(s))
- `getattr` (4 edge(s))
- `time` (4 edge(s))
- `join` (3 edge(s))
- `startswith` (3 edge(s))
- `backend/splunk/client/__init__.py::SplunkRestClient` (2 edge(s))
- `login` (2 edge(s))
- `max` (2 edge(s))
- `split` (1 edge(s))

### Incoming

- `backend/splunk/datamodel/cim_schema.py` (12 edge(s))
- `backend/tests/test_cim_datamodel_catalog.py` (3 edge(s))
- `len` (2 edge(s))
- `CimDatamodelSchema` (1 edge(s))
- `CimObjectInfo` (1 edge(s))
- `summary_for_prompt` (1 edge(s))
- `backend/tests/test_splunk_live_mcp_saia.py` (1 edge(s))
