"""
Discover CIM data model structure via ``| datamodelsimple`` (Splunk_SA_CIM).

Splunk docs: https://help.splunk.com/?resourceId=CIM_User_UsetheCIMtovalidateyourdata
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from config import Settings
from splunk.client import SplunkRestClient

logger = logging.getLogger(__name__)

_CIM_APP = "Splunk_SA_CIM"
_CACHE_TTL_SEC = 3600
_schema_cache: Dict[str, Tuple[float, "CimDatamodelSchema"]] = {}
_catalog_cache: Dict[str, Tuple[float, "CimDatamodelCatalog"]] = {}


@dataclass(frozen=True)
class CimObjectInfo:
    name: str
    lineage: str


@dataclass(frozen=True)
class CimDatamodelCatalog:
    """All CIM data model names reported by ``| datamodelsimple type=models``."""

    models: Tuple[str, ...] = field(default_factory=tuple)

    def summary_for_prompt(self, *, primary_datamodel: str = "", max_listed: int = 80) -> str:
        lines = ["CIM datamodels available on this Splunk deployment (datamodelsimple type=models):"]
        for name in self.models[:max_listed]:
            marker = " [primary for this alert]" if name == primary_datamodel else ""
            lines.append("  - {0}{1}".format(name, marker))
        if len(self.models) > max_listed:
            lines.append("  ... and {0} more".format(len(self.models) - max_listed))
        if primary_datamodel:
            lines.append("Use datamodel={0} for this investigation unless the question clearly needs another model.".format(
                primary_datamodel
            ))
        return "\n".join(lines)


@dataclass
class CimDatamodelSchema:
    datamodel: str
    objects: List[CimObjectInfo] = field(default_factory=list)
    attributes: List[Dict[str, str]] = field(default_factory=list)

    def root_object(self) -> Optional[CimObjectInfo]:
        for obj in self.objects:
            if obj.lineage == self.datamodel or obj.name == self.datamodel:
                return obj
        return self.objects[0] if self.objects else None

    def object_for_nodename(self, nodename: str) -> Optional[CimObjectInfo]:
        nodename = (nodename or "").strip()
        for obj in self.objects:
            if obj.lineage == nodename:
                return obj
        return None

    def field_prefix_for_nodename(self, nodename: str) -> str:
        """tstats field prefix (e.g. Failed_Authentication) for a nodename lineage."""
        obj = self.object_for_nodename(nodename)
        if obj:
            return obj.name
        if "." in nodename:
            return nodename.split(".")[-1]
        return nodename or self.datamodel

    def attribute_names(self, *, nodename: Optional[str] = None, object_name: Optional[str] = None) -> List[str]:
        names: List[str] = []
        prefix = self.field_prefix_for_nodename(nodename) if nodename else (object_name or "")
        for row in self.attributes:
            attr = row.get("attribute") or ""
            lineage = row.get("lineage") or ""
            row_nodename = row.get("nodename") or ""
            if not attr or attr.startswith("_"):
                continue
            if nodename:
                if row_nodename != nodename and not lineage.startswith(prefix + "."):
                    if lineage not in ("host", "source", "sourcetype"):
                        continue
            elif object_name:
                if not lineage.startswith(object_name + ".") and lineage != object_name:
                    if lineage not in ("host", "source", "sourcetype"):
                        continue
            if attr not in names:
                names.append(attr)
        return names

    def prefixed_field(
        self,
        attr: str,
        *,
        nodename: Optional[str] = None,
        object_name: Optional[str] = None,
    ) -> str:
        """Map bare attribute to tstats field using lineage from the matching nodename/object."""
        if nodename:
            for row in self.attributes:
                if row.get("attribute") != attr:
                    continue
                if row.get("nodename") == nodename:
                    lineage = row.get("lineage") or ""
                    if lineage:
                        return lineage
            prefix = self.field_prefix_for_nodename(nodename)
            return "{0}.{1}".format(self.datamodel, attr) if nodename != self.datamodel else "{0}.{1}".format(prefix, attr)

        obj = object_name or (self.root_object().name if self.root_object() else self.datamodel)
        for row in self.attributes:
            if row.get("attribute") == attr:
                lineage = row.get("lineage") or ""
                if "." in lineage:
                    return lineage
                if lineage in ("host", "source", "sourcetype", "_time", "_raw"):
                    return lineage
        return "{0}.{1}".format(obj, attr)

    def schema_summary_for_prompt(self, *, max_objects: int = 8, max_attrs_per_object: int = 12) -> str:
        lines = ["datamodel={0}".format(self.datamodel)]
        lines.append("objects (parent → child lineage):")
        for obj in self.objects[:max_objects]:
            lines.append("  - {0} lineage={1}".format(obj.name, obj.lineage))
        shown = 0
        for obj in self.objects[:max_objects]:
            attrs = self.attribute_names(nodename=obj.lineage)[:max_attrs_per_object]
            if not attrs:
                continue
            lines.append("fields for nodename={0}:".format(obj.lineage))
            for a in attrs:
                lines.append("  - {0}".format(self.prefixed_field(a, nodename=obj.lineage)))
            shown += 1
            if shown >= max_objects:
                break
        return "\n".join(lines)


def infer_cim_datamodel(normalized: Dict[str, Any], search_name: str = "") -> str:
    """Pick a CIM model from alert tags / search name; default Authentication."""
    tags_raw = normalized.get("tag") or normalized.get("tags") or []
    tags: List[str] = []
    if isinstance(tags_raw, list):
        tags = [str(t).lower() for t in tags_raw]
    elif isinstance(tags_raw, str):
        tags = [tags_raw.lower()]

    name_l = (search_name or "").lower()
    tag_set = set(tags)

    if "authentication" in tag_set or "auth" in name_l:
        return "Authentication"
    if "network" in tag_set or "traffic" in name_l:
        return "Network_Traffic"
    if "malware" in tag_set:
        return "Malware"
    if "endpoint" in tag_set or "process" in name_l:
        return "Endpoint"
    if "intrusion" in tag_set or "ids" in name_l:
        return "Intrusion_Detection"
    return "Authentication"


def _attr_key(row: Dict[str, str]) -> Tuple[str, str, str]:
    return (
        row.get("attribute") or "",
        row.get("lineage") or "",
        row.get("nodename") or "",
    )


def _merge_attributes(existing: List[Dict[str, str]], new_rows: List[Dict[str, str]]) -> None:
    seen = {_attr_key(r) for r in existing}
    for row in new_rows:
        k = _attr_key(row)
        if k in seen or not k[0]:
            continue
        seen.add(k)
        existing.append(row)


async def _run_datamodelsimple(
    client: SplunkRestClient,
    session_key: str,
    spl: str,
    *,
    app: str,
) -> List[Dict[str, Any]]:
    return await client.oneshot_search(
        session_key,
        spl,
        app=app,
        owner="nobody",
    )


async def _fetch_attributes_for_object(
    client: SplunkRestClient,
    session_key: str,
    *,
    datamodel: str,
    obj: CimObjectInfo,
    cim_app: str,
) -> List[Dict[str, str]]:
    """Attributes for one dataset via nodename=lineage (child-accurate)."""
    rows = await _run_datamodelsimple(
        client,
        session_key,
        "| datamodelsimple type=attributes datamodel={0} nodename={1}".format(
            datamodel,
            obj.lineage,
        ),
        app=cim_app,
    )
    out: List[Dict[str, str]] = []
    for r in rows:
        attr = str(r.get("attribute") or "")
        if not attr:
            continue
        out.append(
            {
                "attribute": attr,
                "lineage": str(r.get("lineage") or ""),
                "nodename": obj.lineage,
                "object": obj.name,
            }
        )
    return out


def _parse_model_name_from_row(row: Dict[str, Any]) -> Optional[str]:
    for key in ("model", "datamodel", "name", "title", "displayName"):
        val = row.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


async def fetch_cim_datamodel_catalog(
    settings: Settings,
    *,
    app: Optional[str] = None,
    use_cache: bool = True,
) -> Optional[CimDatamodelCatalog]:
    """
    List all CIM data models on the Splunk instance via ``| datamodelsimple type=models``.

    Returns None when credentials are missing or discovery fails.
    """
    cim_app = (app or getattr(settings, "tsoc_cim_spl_app", None) or _CIM_APP).strip()
    if not getattr(settings, "tsoc_cim_fetch_all_models", True):
        return None

    cache_key = "catalog@{0}".format(cim_app)
    if use_cache and cache_key in _catalog_cache:
        ts, cached = _catalog_cache[cache_key]
        if time.time() - ts < _CACHE_TTL_SEC:
            return cached

    if not settings.splunk_username or not settings.splunk_password:
        return None

    client = SplunkRestClient(settings)
    try:
        session_key = await client.login()
    except Exception as e:
        logger.info("cim_catalog login failed: %s", e)
        return None

    try:
        rows = await _run_datamodelsimple(
            client,
            session_key,
            "| datamodelsimple type=models",
            app=cim_app,
        )
        names: List[str] = []
        for row in rows:
            name = _parse_model_name_from_row(row)
            if name and name not in names:
                names.append(name)
        names.sort()
        catalog = CimDatamodelCatalog(models=tuple(names))
        logger.info("cim_catalog ok app=%s model_count=%d", cim_app, len(names))
        _catalog_cache[cache_key] = (time.time(), catalog)
        return catalog
    except Exception as e:
        logger.info("cim_catalog fetch failed: %s", e)
        return None


def schema_summary_limits(
    schema: Optional[CimDatamodelSchema],
    *,
    full_fields: bool = True,
    max_objects: int = 15,
    max_attrs_per_object: int = 12,
) -> Tuple[int, int]:
    """Return (max_objects, max_attrs_per_object) for prompt building."""
    if full_fields and schema:
        n_obj = len(schema.objects) or max_objects
        max_a = 0
        for obj in schema.objects:
            max_a = max(max_a, len(schema.attribute_names(nodename=obj.lineage)))
        return n_obj, max(max_a, max_attrs_per_object) or max_attrs_per_object
    return max_objects, max_attrs_per_object


def build_cim_schema_summary_for_prompt(
    *,
    catalog: Optional[CimDatamodelCatalog],
    schema: Optional[CimDatamodelSchema],
    primary_datamodel: str,
    include_catalog: bool = False,
    max_objects: int = 8,
    max_attrs_per_object: int = 12,
    full_fields: bool = False,
) -> str:
    """
    Schema text for SPL generation.

    Default: **selected datamodel only** (objects + prefixed field paths).
    Catalog (type=models list) is omitted unless ``include_catalog=True`` —
    use that only for datamodel *selection*, not per-question SPL calls.
    """
    mo, ma = schema_summary_limits(
        schema,
        full_fields=full_fields,
        max_objects=max_objects,
        max_attrs_per_object=max_attrs_per_object,
    )
    parts: List[str] = []
    if include_catalog and catalog and catalog.models:
        parts.append(catalog.summary_for_prompt(primary_datamodel=primary_datamodel))
    if schema:
        parts.append("CIM datamodel schema (use these exact field paths in tstats):")
        parts.append(schema.schema_summary_for_prompt(
            max_objects=mo,
            max_attrs_per_object=ma,
        ))
    return "\n\n".join(parts)


async def fetch_cim_datamodel_schema(
    settings: Settings,
    datamodel: str,
    *,
    app: Optional[str] = None,
    use_cache: bool = True,
) -> Optional[CimDatamodelSchema]:
    """
    Run datamodelsimple: objects list + attributes per object (nodename=lineage).

    Returns None when Splunk credentials are missing or discovery fails.
    """
    dm = (datamodel or "").strip()
    if not dm:
        return None

    cim_app = (app or getattr(settings, "tsoc_cim_spl_app", None) or _CIM_APP).strip()
    cache_key = "{0}@{1}".format(dm, cim_app)
    if use_cache and cache_key in _schema_cache:
        ts, cached = _schema_cache[cache_key]
        if time.time() - ts < _CACHE_TTL_SEC:
            return cached

    if not settings.splunk_username or not settings.splunk_password:
        return None

    max_objs = int(getattr(settings, "tsoc_cim_schema_max_objects", 15) or 15)

    client = SplunkRestClient(settings)
    try:
        session_key = await client.login()
    except Exception as e:
        logger.info("cim_schema login failed: %s", e)
        return None

    try:
        obj_rows = await _run_datamodelsimple(
            client,
            session_key,
            "| datamodelsimple type=objects datamodel={0}".format(dm),
            app=cim_app,
        )
        objects = [
            CimObjectInfo(
                name=str(r.get("object") or ""),
                lineage=str(r.get("lineage") or r.get("object") or ""),
            )
            for r in obj_rows
            if r.get("object")
        ]

        attributes: List[Dict[str, str]] = []
        for obj in objects[:max_objs]:
            try:
                chunk = await _fetch_attributes_for_object(
                    client,
                    session_key,
                    datamodel=dm,
                    obj=obj,
                    cim_app=cim_app,
                )
                _merge_attributes(attributes, chunk)
            except Exception as e:
                logger.info(
                    "cim_schema attributes failed datamodel=%s nodename=%s: %s",
                    dm,
                    obj.lineage,
                    e,
                )

        if not attributes and objects:
            root = objects[0]
            try:
                attr_rows = await _run_datamodelsimple(
                    client,
                    session_key,
                    "| datamodelsimple type=attributes datamodel={0} object={1}".format(
                        dm,
                        root.name,
                    ),
                    app=cim_app,
                )
                fallback = [
                    {
                        "attribute": str(r.get("attribute") or ""),
                        "lineage": str(r.get("lineage") or ""),
                        "nodename": root.lineage,
                        "object": root.name,
                    }
                    for r in attr_rows
                    if r.get("attribute")
                ]
                _merge_attributes(attributes, fallback)
            except Exception as e:
                logger.info("cim_schema root attributes fallback failed: %s", e)

        schema = CimDatamodelSchema(datamodel=dm, objects=objects, attributes=attributes)
        logger.info(
            "cim_schema ok datamodel=%s objects=%d attribute_rows=%d",
            dm,
            len(objects),
            len(attributes),
        )
        _schema_cache[cache_key] = (time.time(), schema)
        return schema
    except Exception as e:
        logger.info("cim_schema fetch failed datamodel=%s: %s", dm, e)
        return None
