"""User inventory CRUD."""

from __future__ import annotations

from typing import List

from config import Settings
from models.inventory import UserCreate, UserRecord, UserUpdate
from services.inventory._db import dynamic_update, is_unique_violation, raise_if_delete_missing
from services.inventory.exceptions import InventoryConflictError, InventoryNotFoundError
from services.splunk_json_store import ensure_pool

_USER_SELECT = "user_id, display_name, email, department, risk_score, description"


async def list_users(settings: Settings) -> List[UserRecord]:
    pool = await ensure_pool(settings)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT {0} FROM tsoc_users ORDER BY user_id".format(_USER_SELECT)
        )
    return [UserRecord(**dict(r)) for r in rows]


async def get_user(settings: Settings, user_id: str) -> UserRecord:
    pool = await ensure_pool(settings)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT {0} FROM tsoc_users WHERE user_id = $1".format(_USER_SELECT),
            user_id,
        )
    if row is None:
        raise InventoryNotFoundError("user not found: {0}".format(user_id))
    return UserRecord(**dict(row))


async def create_user(settings: Settings, body: UserCreate) -> UserRecord:
    pool = await ensure_pool(settings)
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tsoc_users (user_id, display_name, email, department, risk_score, description)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                body.user_id,
                body.display_name,
                body.email,
                body.department,
                body.risk_score,
                body.description,
            )
    except Exception as e:
        if is_unique_violation(e):
            raise InventoryConflictError("user_id already exists: {0}".format(body.user_id)) from e
        raise
    return await get_user(settings, body.user_id)


async def update_user(settings: Settings, user_id: str, body: UserUpdate) -> UserRecord:
    await get_user(settings, user_id)
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        return await get_user(settings, user_id)
    await dynamic_update(
        settings, table="tsoc_users", id_column="user_id", id_value=user_id, fields=fields
    )
    return await get_user(settings, user_id)


async def delete_user(settings: Settings, user_id: str) -> None:
    pool = await ensure_pool(settings)
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM tsoc_users WHERE user_id = $1", user_id)
    raise_if_delete_missing(result, "user", user_id)
