"""CIM datamodel catalog (type=models)."""

from __future__ import annotations

from splunk.datamodel.cim_schema import (
    CimDatamodelCatalog,
    _parse_model_name_from_row,
    build_cim_schema_summary_for_prompt,
)


def test_parse_model_name_from_row() -> None:
    assert _parse_model_name_from_row({"model": "Authentication"}) == "Authentication"
    assert _parse_model_name_from_row({"datamodel": "Network_Traffic"}) == "Network_Traffic"
    assert _parse_model_name_from_row({}) is None


def test_catalog_summary_lists_all_models() -> None:
    catalog = CimDatamodelCatalog(
        models=("Authentication", "Endpoint", "Network_Traffic", "Malware"),
    )
    text = catalog.summary_for_prompt(primary_datamodel="Authentication")
    assert "Network_Traffic" in text
    assert "Malware" in text
    assert "[primary for this alert]" in text


def test_build_cim_schema_summary_combines_catalog_and_schema() -> None:
    from splunk.datamodel.cim_schema import CimDatamodelSchema, CimObjectInfo

    catalog = CimDatamodelCatalog(models=("Authentication", "Endpoint"))
    schema = CimDatamodelSchema(
        datamodel="Authentication",
        objects=[CimObjectInfo(name="Authentication", lineage="Authentication")],
        attributes=[{"attribute": "user", "lineage": "Authentication.user", "nodename": "Authentication"}],
    )
    out = build_cim_schema_summary_for_prompt(
        catalog=catalog,
        schema=schema,
        primary_datamodel="Authentication",
        include_catalog=True,
    )
    assert "type=models" in out
    assert "Endpoint" in out
    assert "CIM datamodel schema" in out

    slim = build_cim_schema_summary_for_prompt(
        catalog=catalog,
        schema=schema,
        primary_datamodel="Authentication",
        include_catalog=False,
    )
    assert "Endpoint" not in slim
    assert "Authentication.user" in slim
