"""Post-ingest background work: persist summary and optional agent triage."""

from __future__ import annotations

import logging
import traceback
from typing import Any, Dict, Optional

from config import Settings
from models.agents import AgentTriageRequest
from models.handoff import SplunkAlertIngest
from services.alert.agent_triage import run_agent_triage
from services.soc_rag.index_writer import schedule_alert_index
from services.splunk_json_store import persist_splunk_ingest_summary, submit_hec_event

logger = logging.getLogger(__name__)


async def persist_ingest_background_error(
    settings: Settings,
    handoff: SplunkAlertIngest,
    error: str,
    *,
    stage: str = "post_ingest",
) -> None:
    await submit_hec_event(
        settings,
        {
            "tsoc_record_type": "ingest_background_error",
            "sid": handoff.sid,
            "search_name": handoff.search_name,
            "stage": stage,
            "error": error,
        },
    )


async def run_post_ingest(
    settings: Settings,
    handoff: SplunkAlertIngest,
    enriched: Dict[str, Any],
    *,
    auto_analyze: bool,
) -> None:
    """Run after webhook enrich: persist ingest summary and optional triage pipeline."""
    try:
        await persist_splunk_ingest_summary(
            settings,
            handoff,
            splunk_results_row_count=int(enriched.get("splunk_results_row_count") or 0),
            splunk_results=list(enriched.get("splunk_results") or []),
        )
    except Exception as e:
        logger.warning("post_ingest persist summary failed sid=%s: %s", handoff.sid, e, exc_info=True)
        await persist_ingest_background_error(settings, handoff, str(e), stage="persist_summary")
        return

    schedule_alert_index(
        settings,
        handoff,
        splunk_results=list(enriched.get("splunk_results") or []),
    )

    if not auto_analyze or settings.tsoc_ingest_auto_analyze_pipeline == "none":
        return

    if settings.tsoc_ingest_auto_analyze_pipeline != "triage":
        await persist_ingest_background_error(
            settings,
            handoff,
            "unsupported pipeline: {0}".format(settings.tsoc_ingest_auto_analyze_pipeline),
            stage="auto_analyze",
        )
        return

    rows = list(enriched.get("splunk_results") or [])
    norm = handoff.normalized or {}
    if not norm and rows:
        norm = dict(rows[0])

    body = AgentTriageRequest(
        normalized=norm,
        search_name=handoff.search_name,
        sid=handoff.sid,
        splunk_results=rows,
    )
    try:
        await run_agent_triage(settings, body)
    except Exception as e:
        tb = traceback.format_exc()
        logger.warning("post_ingest triage failed sid=%s: %s", handoff.sid, e, exc_info=True)
        await persist_ingest_background_error(settings, handoff, "{0}\n{1}".format(e, tb), stage="triage")
