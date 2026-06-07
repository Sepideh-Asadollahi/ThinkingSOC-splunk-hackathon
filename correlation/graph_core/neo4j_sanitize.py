from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def sanitize_neo4j_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "to_native"):
        value = value.to_native()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {str(k): sanitize_neo4j_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_neo4j_value(v) for v in value]
    return value
