"""Execute investigation SPL on Splunk (MCP splunk_run_query or REST oneshot)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from config import Settings, mcp_configured

if TYPE_CHECKING:
    from splunk.mcp.client import SplunkMcpClient
from models.analysis import InvestigationQuestionItem, SplSearchResult
from services.investigation.spl_predict_pipeline import (
    SPL_ALL_TIME_WINDOW,
    all_time_bounds,
    default_investigation_time_window,
    execute_spl_via_mcp,
    rows_from_mcp_result,
)
from services.investigation.spl_tstats_sanitize import sanitize_spl_draft, spl_execute_app
from splunk.client import SplunkRestClient

logger = logging.getLogger(__name__)

_MAX_ROWS = 50
_MAX_CELL_STR_CHARS = 320
_MAX_LIST_ITEMS = 25

# Re-export for tests and script imports.
_rows_from_mcp_result = rows_from_mcp_result
_default_time_window = default_investigation_time_window


def needs_spl_execution_refine(result: Optional[SplSearchResult]) -> bool:
    """True when we should run LiteLLM refine (error or zero rows)."""
    if result is None:
        return False
    if result.error and str(result.error).strip():
        return True
    return (result.row_count or 0) == 0


def _readable_cell(value: Any) -> Any:
    if isinstance(value, list):
        out = list(value[:_MAX_LIST_ITEMS])
        extra = len(value) - len(out)
        if extra > 0:
            out.append("... (+{0} more)".format(extra))
        return out
    if isinstance(value, str) and len(value) > _MAX_CELL_STR_CHARS:
        extra = len(value) - _MAX_CELL_STR_CHARS
        return value[:_MAX_CELL_STR_CHARS] + "... (+{0} chars)".format(extra)
    return value


def _readable_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append({str(k): _readable_cell(v) for k, v in row.items()})
    return out


async def execute_investigation_spl(
    settings: Settings,
    items: List[InvestigationQuestionItem],
) -> List[InvestigationQuestionItem]:
    """Run each item's SPL; soft-fail when credentials missing."""
    if not getattr(settings, "tsoc_execute_investigation_spl", True):
        return items
    if not items:
        return items
    if not settings.splunk_username or not settings.splunk_password:
        return items

    client = SplunkRestClient(settings)
    try:
        session_key = await client.login()
    except Exception as e:
        logger.info("investigation_spl_execute login skipped: %s", e)
        return items

    mcp_client: Optional[SplunkMcpClient] = None
    if mcp_configured(settings) and bool(getattr(settings, "tsoc_spl_execute_via_mcp", True)):
        from splunk.mcp.client import SplunkMcpClient

        try:
            mcp_client = SplunkMcpClient(settings)
            await mcp_client.ensure_ready()
        except Exception as e:
            logger.info("investigation_spl_execute MCP init skipped: %s", e)
            mcp_client = None

    out: List[InvestigationQuestionItem] = []
    for item in items:
        out.append(
            await execute_investigation_item(
                settings,
                item,
                client=client,
                session_key=session_key,
                mcp_client=mcp_client,
            )
        )
    return out


async def execute_investigation_item(
    settings: Settings,
    item: InvestigationQuestionItem,
    *,
    client: SplunkRestClient,
    session_key: str,
    app: Optional[str] = None,
    mcp_client: Optional["SplunkMcpClient"] = None,
) -> InvestigationQuestionItem:
    """Run SPL for one investigation question (MCP preferred, REST fallback)."""
    spl = sanitize_spl_draft(item.spl or "")
    if not spl:
        return item.model_copy(
            update={
                "spl_results": SplSearchResult(
                    row_count=0,
                    rows=[],
                    error="empty SPL after sanitize",
                ),
            }
        )
    run_app = app or spl_execute_app(settings, spl)
    earliest, latest = all_time_bounds(settings)

    result = await _run_one(
        settings,
        client,
        session_key,
        spl,
        app=run_app,
        earliest_time=earliest,
        latest_time=latest,
        mcp_client=mcp_client,
    )
    return item.model_copy(
        update={"spl_results": result, "spl": spl, "time_window": SPL_ALL_TIME_WINDOW}
    )


async def _run_one(
    settings: Settings,
    client: SplunkRestClient,
    session_key: str,
    spl: str,
    *,
    app: str,
    earliest_time: Optional[str] = None,
    latest_time: Optional[str] = None,
    mcp_client: Optional["SplunkMcpClient"] = None,
) -> SplSearchResult:
    if not (spl or "").strip():
        return SplSearchResult(row_count=0, rows=[], error="empty SPL")

    earliest_time, latest_time = all_time_bounds(settings)

    use_mcp = bool(getattr(settings, "tsoc_spl_execute_via_mcp", True))
    mcp_failure: Optional[str] = None
    if use_mcp and mcp_configured(settings):
        mcp_result = await execute_spl_via_mcp(
            settings,
            spl,
            row_limit=_MAX_ROWS,
            earliest_time=earliest_time,
            latest_time=latest_time,
            mcp_client=mcp_client,
        )
        if not mcp_result.error:
            if (mcp_result.row_count or 0) > 0:
                return mcp_result.model_copy(
                    update={
                        "rows": _readable_rows(mcp_result.rows or []),
                        "execution_transport": "mcp",
                    }
                )
            mcp_failure = "MCP returned zero rows"
            logger.info(
                "MCP run_query returned 0 rows, fallback to REST oneshot spl_len=%d",
                len(spl),
            )
        else:
            mcp_failure = str(mcp_result.error)
            logger.info("MCP run_query failed, fallback to REST oneshot: %s", mcp_result.error)

    try:
        rows = await client.oneshot_search(
            session_key,
            spl,
            app=app,
            owner="nobody",
            earliest_time=earliest_time,
            latest_time=latest_time,
        )
        capped = rows[:_MAX_ROWS]
        return SplSearchResult(
            row_count=len(rows),
            rows=_readable_rows(capped),
            truncated=len(rows) > _MAX_ROWS,
            execution_transport="rest",
        )
    except Exception as e:
        logger.info("investigation_spl_execute failed spl_len=%d: %s", len(spl), e)
        rest_error = str(e)
        combined = (
            "MCP unavailable ({0}); Splunk REST API failed ({1})".format(
                mcp_failure, rest_error
            )
            if mcp_failure
            else "Splunk REST API failed ({0})".format(rest_error)
        )
        return SplSearchResult(row_count=0, rows=[], error=combined)
