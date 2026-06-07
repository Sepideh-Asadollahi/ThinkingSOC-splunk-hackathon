from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List

import httpx

from api.app_errors import AppError, splunk_job_not_found, splunk_rest_error
from config import Settings
from models.handoff import SplunkAlertIngest
from splunk.client import SplunkRestClient

logger = logging.getLogger(__name__)

_SPLUNK_SID_PREFIXES = (
    "scheduler",
    "rt_",
    "subsearch",
    "summary",
    "dispatch",
    "search",
)


def _looks_like_splunk_job_sid(sid: str | None) -> bool:
    """Heuristic: real Splunk search IDs usually contain ``__`` or known prefixes."""
    value = (sid or "").strip()
    if not value:
        return False
    if "__" in value:
        return True
    lower = value.lower()
    return any(lower.startswith(prefix) for prefix in _SPLUNK_SID_PREFIXES)


def _splunk_rest_configured(settings: Settings) -> bool:
    return bool(settings.splunk_username and settings.splunk_password)


def _job_dispatch_state(job: Dict[str, Any]) -> str:
    entries = job.get("entry")
    if isinstance(entries, list) and entries and isinstance(entries[0], dict):
        content = entries[0].get("content")
        if isinstance(content, dict) and content.get("dispatchState") is not None:
            return str(content.get("dispatchState"))
    return "unknown"


def _build_payload(
    handoff: SplunkAlertIngest,
    *,
    job: Dict[str, Any],
    results: List[Dict[str, Any]],
    source: str,
) -> Dict[str, Any]:
    return {
        "handoff": handoff.model_dump(),
        "splunk_job": job,
        "splunk_results_row_count": len(results),
        "splunk_results": results,
        "enrichment_source": source,
    }


async def _fetch_results_via_rest(
    handoff: SplunkAlertIngest,
    settings: Settings,
    sid: str,
) -> Dict[str, Any]:
    client = SplunkRestClient(settings)
    session_key = await client.login()
    job = await client.get_job(sid, session_key)
    results = await client.fetch_all_results(sid, session_key)
    return _build_payload(handoff, job=job, results=results, source="splunk_rest")


async def enrich_alert_from_splunk(handoff: SplunkAlertIngest, settings: Settings) -> Dict[str, Any]:
    t0 = time.perf_counter()

    from services.soc_analysis.analysis_audit import splunk_job_sid

    inline_results = [dict(row) for row in handoff.results if isinstance(row, dict)]
    normalized = dict(handoff.normalized or {})
    sid = splunk_job_sid(handoff.sid)

    # Splunk alert action posts only ``result`` (first row). When we have a real job
    # sid + REST credentials, load the full job result set — do not stop at inline rows.
    if sid and _looks_like_splunk_job_sid(sid) and _splunk_rest_configured(settings):
        try:
            payload = await _fetch_results_via_rest(handoff, settings, sid)
            if inline_results:
                logger.info(
                    "ingest enrich sid=%s webhook_inline_rows=%d splunk_rest_rows=%d "
                    "decision=use_splunk_rest (webhook sends first row only)",
                    sid,
                    len(inline_results),
                    int(payload.get("splunk_results_row_count") or 0),
                )
            _maybe_log(settings, payload, handoff, t0, job_dispatch=_job_dispatch_state(payload.get("splunk_job") or {}))
            return payload
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404 and inline_results:
                logger.warning(
                    "ingest sid=%s Splunk job 404 — fallback to webhook inline_rows=%d",
                    sid,
                    len(inline_results),
                )
                payload = _build_payload(handoff, job={}, results=inline_results, source="inline_results_rest_404")
                _maybe_log(settings, payload, handoff, t0, job_dispatch="inline_rest_404")
                return payload
            if exc.response.status_code == 404 and normalized:
                logger.warning(
                    "ingest sid=%s Splunk job 404 — using normalized fallback row",
                    sid,
                )
                payload = _build_payload(handoff, job={}, results=[normalized], source="normalized_splunk_404")
                _maybe_log(settings, payload, handoff, t0, job_dispatch="normalized_splunk_404")
                return payload
            raise splunk_rest_error(exc, sid=sid) from exc
        except Exception as exc:
            if inline_results:
                logger.warning(
                    "ingest sid=%s Splunk REST failed (%s) — fallback to webhook inline_rows=%d",
                    sid,
                    exc,
                    len(inline_results),
                )
                payload = _build_payload(handoff, job={}, results=inline_results, source="inline_results_rest_error")
                _maybe_log(settings, payload, handoff, t0, job_dispatch="inline_rest_error")
                return payload
            raise

    if inline_results:
        logger.info(
            "ingest enrich sid=%s webhook_inline_rows=%d decision=use_inline_only "
            "(no REST credentials or non-job sid)",
            sid or handoff.sid,
            len(inline_results),
        )
        payload = _build_payload(handoff, job={}, results=inline_results, source="inline_results")
        _maybe_log(settings, payload, handoff, t0, job_dispatch="inline")
        return payload

    if not sid:
        if normalized:
            payload = _build_payload(handoff, job={}, results=[normalized], source="normalized_only")
            _maybe_log(settings, payload, handoff, t0, job_dispatch="normalized_only")
            return payload
        raise AppError.bad_request(
            "sid is required to fetch job/results from Splunk REST",
            code="missing_sid",
            reason="Provide sid from the Splunk alert, or include result/results/normalized in the webhook body.",
        )

    if normalized and not _looks_like_splunk_job_sid(sid):
        logger.info(
            "ingest sid=%s looks like demo/offline id — using normalized row without Splunk REST",
            sid,
        )
        payload = _build_payload(handoff, job={}, results=[normalized], source="normalized_demo_sid")
        _maybe_log(settings, payload, handoff, t0, job_dispatch="normalized_demo_sid")
        return payload

    if not _splunk_rest_configured(settings):
        if normalized:
            payload = _build_payload(handoff, job={}, results=[normalized], source="normalized_no_rest_creds")
            _maybe_log(settings, payload, handoff, t0, job_dispatch="normalized_no_rest_creds")
            return payload
        raise AppError.bad_request(
            "Splunk REST credentials required to fetch job results",
            code="missing_splunk_credentials",
            reason="Set SPLUNK_USERNAME and SPLUNK_PASSWORD in backend/.env",
        )

    payload = await _fetch_results_via_rest(handoff, settings, sid)
    _maybe_log(settings, payload, handoff, t0, job_dispatch=_job_dispatch_state(payload.get("splunk_job") or {}))
    return payload


def _maybe_log(
    settings: Settings,
    payload: Dict[str, Any],
    handoff: SplunkAlertIngest,
    t0: float,
    *,
    job_dispatch: str,
) -> None:
    if settings.tsoc_alert_log_path:
        try:
            with open(settings.tsoc_alert_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        except OSError as e:
            logger.warning("Could not append to tsoc_alert_log_path: %s", e)

    logger.info(
        "ingest sid=%s search_name=%s rest_rows=%d job_dispatch_state=%s source=%s duration_ms=%.1f",
        handoff.sid,
        handoff.search_name,
        int(payload.get("splunk_results_row_count") or 0),
        job_dispatch,
        payload.get("enrichment_source", "unknown"),
        (time.perf_counter() - t0) * 1000.0,
    )
