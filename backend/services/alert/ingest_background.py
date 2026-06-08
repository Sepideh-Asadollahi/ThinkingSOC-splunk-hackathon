"""Post-ingest background work: persist summary and optional agent triage."""

from __future__ import annotations

import json
import logging
import traceback
from typing import Any, Dict, List, Optional

from config import Settings
from models.agents import AgentTriageRequest
from models.handoff import SplunkAlertIngest
from services.alert.agent_triage import run_agent_triage, run_agent_triage_all_rows
from services.alert.alert_pipeline import enrich_alert_from_splunk
from services.alert.ingest_dedup import claim_storage_sid, release_storage_sid
from services.alert.ingest_request_trace import resolve_ingest_row_index
from services.alert.ingest_row_shape import detect_splunk_result_row_shape, log_splunk_result_row_shape
from services.soc_analysis.analysis_audit import format_row_sid, splunk_job_sid
from services.soc_analysis.soc_analysis_batch import merge_normalized_for_row
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


async def run_triage_for_ingest(
    settings: Settings,
    handoff: SplunkAlertIngest,
    enriched: Dict[str, Any],
    *,
    ingest_trace: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Run triage for this ingest.

    Splunk often sends **one HTTP POST per result row** (same ``sid``, different ``result``).
    In that case we analyze **only the row in this request**, not every REST row again.
    """
    rest_rows: List[Dict[str, Any]] = list(enriched.get("splunk_results") or [])
    webhook_rows: List[Dict[str, Any]] = [r for r in handoff.results if isinstance(r, dict)]
    max_rows = int(getattr(settings, "tsoc_ingest_auto_analyze_max_rows", 50) or 50)
    base_sid = splunk_job_sid(handoff.sid) or (handoff.sid or "")
    trace = ingest_trace or {}

    if len(webhook_rows) == 1:
        webhook_row = webhook_rows[0]
        seq = int(trace.get("request_seq_for_sid") or 0) or None
        idx, match_method = resolve_ingest_row_index(webhook_row, rest_rows, request_seq=seq)
        target_row = rest_rows[idx] if rest_rows and 0 <= idx < len(rest_rows) else webhook_row
        job_row_count = max(len(rest_rows), idx + 1, 1)
        storage_sid = format_row_sid(base_sid, idx, job_row_count)
        merged = merge_normalized_for_row(handoff.normalized or {}, target_row)

        shape = detect_splunk_result_row_shape(
            sid=storage_sid,
            total_rows=1,
            max_rows=1,
        )
        log_splunk_result_row_shape(
            stage="pre_triage_per_http_row",
            search_name=handoff.search_name,
            shape=shape,
            log=logger,
        )
        logger.info(
            "post_ingest triage_mode=per_http_request_row trace_id=%s delivery_hint=%s "
            "request_seq_for_sid=%s storage_sid=%s rest_job_rows=%d rest_row_index=%d "
            "row_match_method=%s webhook_fingerprint=%s analyzing_only_this_http_row=true",
            trace.get("trace_id"),
            trace.get("delivery_hint"),
            trace.get("request_seq_for_sid"),
            storage_sid,
            len(rest_rows),
            idx,
            match_method,
            trace.get("result_fingerprint"),
        )
        logger.info(
            "post_ingest triage_row_payload trace_id=%s storage_sid=%s target_row=%s",
            trace.get("trace_id"),
            storage_sid,
            json.dumps(target_row, ensure_ascii=False, default=str)[:4000],
        )

        if not await claim_storage_sid(storage_sid):
            logger.info(
                "post_ingest dedup_skip storage_sid=%s trace_id=%s reason=duplicate_concurrent_or_recent "
                "(another HTTP POST already handling this row)",
                storage_sid,
                trace.get("trace_id"),
            )
            return

        body = AgentTriageRequest(
            normalized=merged,
            search_name=handoff.search_name,
            sid=storage_sid,
            splunk_results=[target_row],
            row_index=idx,
            job_row_count=job_row_count,
        )
        try:
            await run_agent_triage(settings, body)
        except Exception:
            await release_storage_sid(storage_sid)
            raise
        return

    row_shape = detect_splunk_result_row_shape(
        sid=handoff.sid,
        total_rows=len(rest_rows),
        max_rows=max_rows,
    )
    log_splunk_result_row_shape(
        stage="pre_triage_batch",
        search_name=handoff.search_name,
        shape=row_shape,
        log=logger,
    )
    logger.info(
        "post_ingest triage_mode=batch_all_rest_rows trace_id=%s delivery_hint=%s rest_rows=%d",
        trace.get("trace_id"),
        trace.get("delivery_hint"),
        len(rest_rows),
    )

    norm = handoff.normalized or {}
    if not norm and rest_rows:
        norm = dict(rest_rows[0])

    body = AgentTriageRequest(
        normalized=norm,
        search_name=handoff.search_name,
        sid=handoff.sid,
        splunk_results=rest_rows,
    )
    await run_agent_triage_all_rows(settings, body, max_rows=max_rows)


async def run_buffered_job_triage(
    settings: Settings,
    base_sid: str,
    rows: List[Dict[str, Any]],
    template: SplunkAlertIngest,
) -> None:
    """Flush callback for the per-row webhook buffer: analyze the whole job at once.

    ``rows`` are all the result rows collected from the separate webhook POSTs for this
    ``base_sid``. Splunk often sends only the first row per POST (digest mode) or one row
    per HTTP call; when REST is configured we load the full job result set before triage
    so multi-row alerts become ``{base_sid}-1``, ``{base_sid}-2``, … — not duplicates of row 0.
    """
    handoff = template.model_copy(update={"sid": base_sid, "results": rows})
    try:
        enriched = await enrich_alert_from_splunk(handoff, settings)
    except Exception as exc:
        logger.warning(
            "post_ingest buffered_job enrich failed base_sid=%s webhook_rows=%d: %s",
            base_sid,
            len(rows),
            exc,
            exc_info=True,
        )
        enriched = {
            "splunk_results": rows,
            "splunk_results_row_count": len(rows),
            "enrichment_source": "webhook_row_buffer",
        }
    rest_rows = list(enriched.get("splunk_results") or rows)
    if rest_rows:
        handoff = handoff.model_copy(update={"results": rest_rows})
    logger.info(
        "post_ingest buffered_job base_sid=%s webhook_rows=%d rest_rows=%d search_name=%s",
        base_sid,
        len(rows),
        len(rest_rows),
        template.search_name,
    )
    await run_post_ingest(settings, handoff, enriched, auto_analyze=True)


async def run_post_ingest(
    settings: Settings,
    handoff: SplunkAlertIngest,
    enriched: Dict[str, Any],
    *,
    auto_analyze: bool,
) -> None:
    """Run after webhook enrich: persist ingest summary and optional triage pipeline."""
    ingest_trace = enriched.get("_ingest_http_trace")
    if isinstance(ingest_trace, dict):
        logger.info(
            "post_ingest start trace_id=%s sid=%s delivery_hint=%s request_seq_for_sid=%s",
            ingest_trace.get("trace_id"),
            handoff.sid,
            ingest_trace.get("delivery_hint"),
            ingest_trace.get("request_seq_for_sid"),
        )

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

    try:
        trace_dict = ingest_trace if isinstance(ingest_trace, dict) else None
        await run_triage_for_ingest(
            settings,
            handoff,
            enriched,
            ingest_trace=trace_dict,
        )
    except Exception as e:
        tb = traceback.format_exc()
        logger.warning("post_ingest triage failed sid=%s: %s", handoff.sid, e, exc_info=True)
        await persist_ingest_background_error(settings, handoff, "{0}\n{1}".format(e, tb), stage="triage")
