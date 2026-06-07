"""Inventory and relationship models (LLD §3, Asset service)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class UserRecord(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    risk_score: int = Field(ge=0, le=10)
    description: Optional[str] = None


class UserCreate(UserRecord):
    pass


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    risk_score: Optional[int] = Field(default=None, ge=0, le=10)
    description: Optional[str] = None


class AssetRecord(BaseModel):
    asset_id: str
    asset_type: str
    hostname: Optional[str] = None
    fqdn: Optional[str] = None
    ip: Optional[str] = None
    owner: Optional[str] = None
    criticality: Literal["low", "medium", "high", "critical"] = "medium"
    risk_score: int = Field(ge=0, le=10)
    description: Optional[str] = None


class AssetCreate(AssetRecord):
    pass


class AssetUpdate(BaseModel):
    asset_type: Optional[str] = None
    hostname: Optional[str] = None
    fqdn: Optional[str] = None
    ip: Optional[str] = None
    owner: Optional[str] = None
    criticality: Optional[Literal["low", "medium", "high", "critical"]] = None
    risk_score: Optional[int] = Field(default=None, ge=0, le=10)
    description: Optional[str] = None


class RelationshipRecord(BaseModel):
    relationship_id: str
    user_id: str
    asset_id: str
    description: Optional[str] = None


class RelationshipCreate(RelationshipRecord):
    pass


class RelationshipUpdate(BaseModel):
    user_id: Optional[str] = None
    asset_id: Optional[str] = None
    description: Optional[str] = None
