"""Inventory CRUD: users, assets, relationships (PostgreSQL)."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from api.deps import check_ingest_bearer
from api.http_rid import http_rid
from config import Settings, get_settings
from models.enrichment import EnrichRequest, EnrichmentResult
from models.inventory import (
    AssetCreate,
    AssetRecord,
    AssetUpdate,
    RelationshipCreate,
    RelationshipRecord,
    RelationshipUpdate,
    UserCreate,
    UserRecord,
    UserUpdate,
)
from services.alert.enrichment_resolver import enrich_from_inventory
from services.inventory.inventory_loader import IncompleteOfflineInventoryError, load_inventory_tables
from services.inventory import (
    InventoryConflictError,
    InventoryNotFoundError,
    create_asset,
    create_relationship,
    create_user,
    delete_asset,
    delete_relationship,
    delete_user,
    get_asset,
    get_relationship,
    get_user,
    list_assets,
    list_relationships,
    list_users,
    update_asset,
    update_relationship,
    update_user,
)
from services.splunk_json_store import persist_enrichment_to_splunk, splunk_store_configured

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(check_ingest_bearer)])


def _require_pg(settings: Settings) -> None:
    if not splunk_store_configured(settings):
        raise HTTPException(status_code=503, detail="PostgreSQL not configured; set TSOC_POSTGRES_DSN.")


# --- Users ---


@router.get("/inventory/users", response_model=list[UserRecord])
async def list_users_endpoint(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> list[UserRecord]:
    _require_pg(settings)
    logger.info("api GET /inventory/users rid=%s", http_rid(request))
    return await list_users(settings)


@router.post("/inventory/users", response_model=UserRecord, status_code=201)
async def create_user_endpoint(
    request: Request,
    body: UserCreate,
    settings: Settings = Depends(get_settings),
) -> UserRecord:
    _require_pg(settings)
    try:
        return await create_user(settings, body)
    except InventoryConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("/inventory/users/{user_id}", response_model=UserRecord)
async def get_user_endpoint(
    user_id: str,
    settings: Settings = Depends(get_settings),
) -> UserRecord:
    _require_pg(settings)
    try:
        return await get_user(settings, user_id)
    except InventoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch("/inventory/users/{user_id}", response_model=UserRecord)
async def update_user_endpoint(
    user_id: str,
    body: UserUpdate,
    settings: Settings = Depends(get_settings),
) -> UserRecord:
    _require_pg(settings)
    try:
        return await update_user(settings, user_id, body)
    except InventoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/inventory/users/{user_id}", status_code=204)
async def delete_user_endpoint(
    user_id: str,
    settings: Settings = Depends(get_settings),
) -> None:
    _require_pg(settings)
    try:
        await delete_user(settings, user_id)
    except InventoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# --- Assets ---


@router.get("/inventory/assets", response_model=list[AssetRecord])
async def list_assets_endpoint(settings: Settings = Depends(get_settings)) -> list[AssetRecord]:
    _require_pg(settings)
    return await list_assets(settings)


@router.post("/inventory/assets", response_model=AssetRecord, status_code=201)
async def create_asset_endpoint(
    body: AssetCreate,
    settings: Settings = Depends(get_settings),
) -> AssetRecord:
    _require_pg(settings)
    try:
        return await create_asset(settings, body)
    except InventoryConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("/inventory/assets/{asset_id}", response_model=AssetRecord)
async def get_asset_endpoint(
    asset_id: str,
    settings: Settings = Depends(get_settings),
) -> AssetRecord:
    _require_pg(settings)
    try:
        return await get_asset(settings, asset_id)
    except InventoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch("/inventory/assets/{asset_id}", response_model=AssetRecord)
async def update_asset_endpoint(
    asset_id: str,
    body: AssetUpdate,
    settings: Settings = Depends(get_settings),
) -> AssetRecord:
    _require_pg(settings)
    try:
        return await update_asset(settings, asset_id, body)
    except InventoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/inventory/assets/{asset_id}", status_code=204)
async def delete_asset_endpoint(
    asset_id: str,
    settings: Settings = Depends(get_settings),
) -> None:
    _require_pg(settings)
    try:
        await delete_asset(settings, asset_id)
    except InventoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# --- Relationships ---


@router.get("/inventory/relationships", response_model=list[RelationshipRecord])
async def list_relationships_endpoint(
    settings: Settings = Depends(get_settings),
) -> list[RelationshipRecord]:
    _require_pg(settings)
    return await list_relationships(settings)


@router.post("/inventory/relationships", response_model=RelationshipRecord, status_code=201)
async def create_relationship_endpoint(
    body: RelationshipCreate,
    settings: Settings = Depends(get_settings),
) -> RelationshipRecord:
    _require_pg(settings)
    try:
        return await create_relationship(settings, body)
    except InventoryConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("/inventory/relationships/{relationship_id}", response_model=RelationshipRecord)
async def get_relationship_endpoint(
    relationship_id: str,
    settings: Settings = Depends(get_settings),
) -> RelationshipRecord:
    _require_pg(settings)
    try:
        return await get_relationship(settings, relationship_id)
    except InventoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch("/inventory/relationships/{relationship_id}", response_model=RelationshipRecord)
async def update_relationship_endpoint(
    relationship_id: str,
    body: RelationshipUpdate,
    settings: Settings = Depends(get_settings),
) -> RelationshipRecord:
    _require_pg(settings)
    try:
        return await update_relationship(settings, relationship_id, body)
    except InventoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/inventory/relationships/{relationship_id}", status_code=204)
async def delete_relationship_endpoint(
    relationship_id: str,
    settings: Settings = Depends(get_settings),
) -> None:
    _require_pg(settings)
    try:
        await delete_relationship(settings, relationship_id)
    except InventoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# --- Enrichment ---


@router.post("/inventory/enrich", response_model=EnrichmentResult)
async def enrich_endpoint(
    request: Request,
    body: EnrichRequest,
    settings: Settings = Depends(get_settings),
) -> EnrichmentResult:
    """Match alert fields to inventory; use relationships when only user or asset is known."""
    t0 = time.perf_counter()
    try:
        users, assets, relationships = await load_inventory_tables(
            settings, body.users, body.assets, body.relationships
        )
    except IncompleteOfflineInventoryError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail="Inventory load failed: {0}".format(e),
        ) from e

    out = enrich_from_inventory(body.normalized, users, assets, relationships)
    await persist_enrichment_to_splunk(settings, body.normalized, out)
    logger.info(
        "api POST /inventory/enrich rid=%s user=%s asset=%s confidence=%s duration_ms=%.1f",
        http_rid(request),
        out.resolved_user_id,
        out.resolved_asset_id,
        out.confidence,
        (time.perf_counter() - t0) * 1000.0,
    )
    return out


@router.get("/inventory/status")
async def inventory_status(settings: Settings = Depends(get_settings)) -> dict:
    """Inventory is stored in PostgreSQL only (UI CRUD + enrichment)."""
    return {
        "source": "postgresql",
        "postgres_configured": splunk_store_configured(settings),
    }
