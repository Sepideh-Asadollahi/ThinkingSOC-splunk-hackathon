"""Parse Splunk oneshot / search jobs JSON (output_mode=json) into result rows."""

from __future__ import annotations

from typing import Any, Dict, List


def parse_oneshot_json(data: Any) -> List[Dict[str, Any]]:
    """Extract result rows from Splunk oneshot JSON (output_mode=json)."""
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if not isinstance(data, dict):
        return []
    messages = data.get("messages")
    if isinstance(messages, list):
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            if str(msg.get("type", "")).upper() in ("FATAL", "ERROR"):
                text = msg.get("text") or msg.get("message") or str(msg)
                raise RuntimeError("Splunk search error: {0}".format(text))
    results = data.get("results")
    if isinstance(results, list):
        return [x for x in results if isinstance(x, dict)]
    return []
