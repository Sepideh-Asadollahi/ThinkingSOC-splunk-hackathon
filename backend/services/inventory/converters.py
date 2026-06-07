"""Convert DB rows to plain dicts for enrichment."""

from __future__ import annotations

from typing import Any, Dict

from models.inventory import AssetRecord, RelationshipRecord, UserRecord


def user_to_dict(row: Any) -> Dict[str, Any]:
    return {
        "user_id": row["user_id"],
        "display_name": row["display_name"],
        "email": row["email"],
        "department": row["department"],
        "risk_score": str(row["risk_score"]),
        "description": row["description"],
    }


def asset_to_dict(row: Any) -> Dict[str, Any]:
    return {
        "asset_id": row["asset_id"],
        "asset_type": row["asset_type"],
        "hostname": row["hostname"],
        "fqdn": row["fqdn"],
        "ip": row["ip"],
        "owner": row["owner"],
        "criticality": row["criticality"],
        "risk_score": str(row["risk_score"]),
        "description": row["description"],
    }


def relationship_to_dict(row: Any) -> Dict[str, Any]:
    return {
        "relationship_id": row["relationship_id"],
        "user_id": row["user_id"],
        "asset_id": row["asset_id"],
        "description": row["description"],
    }


def user_record_to_dict(record: UserRecord) -> Dict[str, Any]:
    return user_to_dict(record.model_dump())


def asset_record_to_dict(record: AssetRecord) -> Dict[str, Any]:
    return asset_to_dict(record.model_dump())


def relationship_record_to_dict(record: RelationshipRecord) -> Dict[str, Any]:
    return relationship_to_dict(record.model_dump())
