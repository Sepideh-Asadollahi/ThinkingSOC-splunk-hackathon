"""Compact inventory rows for SOC chat retrieval."""

from __future__ import annotations

from typing import Any, Dict, List

from models.inventory import AssetRecord, RelationshipRecord, UserRecord

from .compact_alert import _build_chunk_text, make_doc_id
from .models import RagAlertDocument


def _row_dict(row: Any) -> Dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, "model_dump"):
        return row.model_dump(mode="json")
    return dict(row)


def compact_user_document(user: UserRecord | Dict[str, Any]) -> RagAlertDocument:
    d = _row_dict(user)
    uid = str(d.get("user_id") or "")
    essential = {
        "user_id": uid,
        "display_name": str(d.get("display_name") or ""),
        "email": str(d.get("email") or ""),
        "department": str(d.get("department") or ""),
        "risk_score": str(d.get("risk_score") or ""),
    }
    summary = "User {0} ({1}) dept={2} risk={3}".format(
        uid,
        essential["display_name"] or "-",
        essential["department"] or "-",
        essential["risk_score"],
    )
    chunk = _build_chunk_text(
        doc_type="inventory_user",
        sid=None,
        search_name=None,
        essential=essential,
        extra_lines=[
            "Inventory user record",
            "Description: {0}".format((d.get("description") or "")[:400]),
        ],
    )
    return RagAlertDocument(
        doc_type="inventory_user",
        doc_id=make_doc_id(uid, 0, "inventory_user"),
        essential=essential,
        summary_line=summary,
        chunk_text=chunk,
        metadata={"doc_type": "inventory_user", **essential},
    )


def compact_asset_document(asset: AssetRecord | Dict[str, Any]) -> RagAlertDocument:
    d = _row_dict(asset)
    aid = str(d.get("asset_id") or "")
    essential = {
        "asset_id": aid,
        "asset_type": str(d.get("asset_type") or ""),
        "hostname": str(d.get("hostname") or ""),
        "fqdn": str(d.get("fqdn") or ""),
        "ip": str(d.get("ip") or ""),
        "owner": str(d.get("owner") or ""),
        "criticality": str(d.get("criticality") or ""),
        "risk_score": str(d.get("risk_score") or ""),
    }
    summary = "Asset {0} host={1} ip={2} criticality={3}".format(
        aid,
        essential["hostname"] or essential["fqdn"] or "-",
        essential["ip"] or "-",
        essential["criticality"],
    )
    chunk = _build_chunk_text(
        doc_type="inventory_asset",
        sid=None,
        search_name=None,
        essential=essential,
        extra_lines=[
            "Inventory asset record",
            "Description: {0}".format((d.get("description") or "")[:400]),
        ],
    )
    return RagAlertDocument(
        doc_type="inventory_asset",
        doc_id=make_doc_id(aid, 0, "inventory_asset"),
        essential=essential,
        summary_line=summary,
        chunk_text=chunk,
        metadata={"doc_type": "inventory_asset", **essential},
    )


def compact_relationship_document(rel: RelationshipRecord | Dict[str, Any]) -> RagAlertDocument:
    d = _row_dict(rel)
    rid = str(d.get("relationship_id") or "")
    uid = str(d.get("user_id") or "")
    aid = str(d.get("asset_id") or "")
    essential = {
        "relationship_id": rid,
        "user_id": uid,
        "asset_id": aid,
    }
    summary = "Relationship user={0} asset={1}".format(uid, aid)
    chunk = _build_chunk_text(
        doc_type="inventory_relationship",
        sid=None,
        search_name=None,
        essential=essential,
        extra_lines=[
            "Inventory user-asset relationship",
            "Description: {0}".format((d.get("description") or "")[:400]),
        ],
    )
    return RagAlertDocument(
        doc_type="inventory_relationship",
        doc_id=make_doc_id(rid or "{0}_{1}".format(uid, aid), 0, "inventory_relationship"),
        essential=essential,
        summary_line=summary,
        chunk_text=chunk,
        metadata={"doc_type": "inventory_relationship", **essential},
    )


async def index_inventory_catalog(settings) -> Dict[str, int]:
    """Index all inventory tables into tsoc_rag_documents (+ Qdrant when enabled)."""
    from services.inventory.assets import list_assets
    from services.inventory.relationships import list_relationships
    from services.inventory.users import list_users

    from .pg_store import upsert_rag_document

    counts = {"inventory_user": 0, "inventory_asset": 0, "inventory_relationship": 0, "errors": 0}
    try:
        for u in await list_users(settings):
            await upsert_rag_document(settings, compact_user_document(u))
            counts["inventory_user"] += 1
        for a in await list_assets(settings):
            await upsert_rag_document(settings, compact_asset_document(a))
            counts["inventory_asset"] += 1
        for r in await list_relationships(settings):
            await upsert_rag_document(settings, compact_relationship_document(r))
            counts["inventory_relationship"] += 1
    except Exception as e:
        counts["errors"] += 1
        raise e
    return counts
