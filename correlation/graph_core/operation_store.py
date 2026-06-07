from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from graph_schemas.analysis import OperationLogEntry, OperationStatusResponse


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OperationStore:
    def __init__(self) -> None:
        self._operations: dict[str, OperationStatusResponse] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        *,
        operation_type: str = "manual_attack_discovery",
        message: str = "Task initiated",
    ) -> str:
        operation_id = str(uuid4())
        now = _utc_now()
        status = OperationStatusResponse(
            operation_id=operation_id,
            operation_type=operation_type,
            status="running",
            message=message,
            detailed_logs=[
                OperationLogEntry(
                    timestamp=now,
                    level="info",
                    message=message,
                )
            ],
            result_payload=None,
            created_at=now,
            last_updated=now,
        )
        async with self._lock:
            self._operations[operation_id] = status
        return operation_id

    async def get(self, operation_id: str) -> Optional[OperationStatusResponse]:
        async with self._lock:
            return self._operations.get(operation_id)

    async def append_log(
        self,
        operation_id: str,
        message: str,
        *,
        level: str = "info",
    ) -> None:
        async with self._lock:
            op = self._operations.get(operation_id)
            if op is None:
                return
            now = _utc_now()
            op.detailed_logs.append(
                OperationLogEntry(timestamp=now, level=level, message=message)
            )
            op.message = message
            op.last_updated = now

    async def complete(
        self,
        operation_id: str,
        result_payload: dict[str, Any],
        *,
        message: str = "Completed",
    ) -> None:
        async with self._lock:
            op = self._operations.get(operation_id)
            if op is None:
                return
            now = _utc_now()
            op.status = "completed"
            op.message = message
            op.result_payload = result_payload
            op.last_updated = now
            op.detailed_logs.append(
                OperationLogEntry(timestamp=now, level="info", message=message)
            )

    async def fail(self, operation_id: str, message: str) -> None:
        async with self._lock:
            op = self._operations.get(operation_id)
            if op is None:
                return
            now = _utc_now()
            op.status = "failed"
            op.message = message
            op.last_updated = now
            op.detailed_logs.append(
                OperationLogEntry(timestamp=now, level="error", message=message)
            )


operation_store = OperationStore()
