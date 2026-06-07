from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from api.deps import check_admin_bearer, rate_limit_sensitive
from api.http_rid import http_rid
from config import Settings, clear_settings_cache, get_settings
from models.integration_settings import (
    IntegrationSettingCreate,
    IntegrationSettingRecord,
    IntegrationSettingUpdate,
)
from services.platform import integration_settings as store

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(check_admin_bearer), Depends(rate_limit_sensitive)])


@router.get("/integrations/settings", response_model=list[IntegrationSettingRecord])
async def list_settings_endpoint(
    settings: Settings = Depends(get_settings),
) -> list[IntegrationSettingRecord]:
    return store.list_integration_settings(settings)


@router.get("/integrations/settings/{setting_id}", response_model=IntegrationSettingRecord)
async def get_setting_endpoint(
    setting_id: str,
    settings: Settings = Depends(get_settings),
) -> IntegrationSettingRecord:
    try:
        return store.get_integration_setting(settings, setting_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="Setting not found") from e


@router.post("/integrations/settings", response_model=IntegrationSettingRecord, status_code=201)
async def create_setting_endpoint(
    request: Request,
    body: IntegrationSettingCreate,
    settings: Settings = Depends(get_settings),
) -> IntegrationSettingRecord:
    try:
        row = store.create_integration_setting(settings, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    logger.info("api POST /integrations/settings rid=%s id=%s", http_rid(request), body.id)
    return row


@router.patch("/integrations/settings/{setting_id}", response_model=IntegrationSettingRecord)
async def update_setting_endpoint(
    request: Request,
    setting_id: str,
    body: IntegrationSettingUpdate,
    settings: Settings = Depends(get_settings),
) -> IntegrationSettingRecord:
    try:
        row, changed = store.update_integration_setting(settings, setting_id, body)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="Setting not found") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if changed:
        clear_settings_cache()
        row = store.get_integration_setting(get_settings(), setting_id)
    logger.info(
        "api PATCH /integrations/settings/%s rid=%s settings_reload=%s",
        setting_id,
        http_rid(request),
        changed,
    )
    return row


@router.delete("/integrations/settings/{setting_id}", status_code=204)
async def delete_setting_endpoint(
    request: Request,
    setting_id: str,
) -> None:
    try:
        changed = store.delete_integration_setting(setting_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(status_code=404, detail="Setting not found") from e
    if changed:
        clear_settings_cache()
    logger.info(
        "api DELETE /integrations/settings/%s rid=%s settings_reload=%s",
        setting_id,
        http_rid(request),
        changed,
    )
