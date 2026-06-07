from __future__ import annotations

import logging
from typing import Any, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver

from correlation_config import Settings, get_settings

logger = logging.getLogger(__name__)

_driver: Optional[AsyncDriver] = None


def discard_driver() -> None:
    global _driver
    _driver = None


def get_driver(settings: Optional[Settings] = None) -> AsyncDriver:
    global _driver
    if _driver is not None:
        return _driver
    s = settings or get_settings()
    _driver = AsyncGraphDatabase.driver(
        s.neo4j_uri,
        auth=(s.neo4j_user, s.neo4j_password),
    )
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


async def reset_driver() -> None:
    global _driver
    if _driver is None:
        return
    try:
        await _driver.close()
    except RuntimeError:
        pass
    _driver = None


async def verify_connectivity(settings: Optional[Settings] = None) -> bool:
    driver = get_driver(settings)
    try:
        await driver.verify_connectivity()
        return True
    except Exception as exc:
        logger.warning("neo4j connectivity failed: %s", exc)
        return False


async def run_read_query(
    query: str,
    parameters: Optional[dict[str, Any]] = None,
    *,
    settings: Optional[Settings] = None,
) -> list[dict[str, Any]]:
    driver = get_driver(settings)
    async with driver.session() as session:
        result = await session.run(query, parameters or {})
        records = await result.data()
        return records


async def run_write_query(
    query: str,
    parameters: Optional[dict[str, Any]] = None,
    *,
    settings: Optional[Settings] = None,
) -> list[dict[str, Any]]:
    driver = get_driver(settings)
    async with driver.session() as session:
        result = await session.run(query, parameters or {})
        records = await result.data()
        return records
