"""Small helpers shared by SAIA MCP tool calls."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.analysis import RootCauseSpl


def append_note(rc: RootCauseSpl, note: str) -> None:
    notes = list(rc.notes or [])
    if note not in notes:
        notes.append(note)
    rc.notes = notes


def saia_tool_args_spl(
    spl: str,
    *,
    search_name: Optional[str] = None,
    extra_context: Optional[str] = None,
    aux_max_chars: int = 32768,
) -> Dict[str, Any]:
    """Arguments for SAIA optimize/explain tools (Splunk MCP Server 1.1+ schema)."""
    args: Dict[str, Any] = {"spl": spl}
    ctx_parts: List[str] = []
    if search_name:
        ctx_parts.append(search_name)
    if extra_context:
        ctx_parts.append(extra_context)
    if ctx_parts:
        cap = max(2048, int(aux_max_chars or 32768))
        args["additional_context"] = " ".join(ctx_parts)[:cap]
    return args


def guess_time_window(spl: str) -> str:
    from services.investigation.spl_predict_pipeline import SPL_ALL_TIME_WINDOW

    _ = spl
    return SPL_ALL_TIME_WINDOW
