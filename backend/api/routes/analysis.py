from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from api.http_rid import http_rid
from api.app_errors import AppError, map_exception
from api.deps import check_ingest_bearer, rate_limit_sensitive
from config import Settings, get_settings
from models.agentic_ops import AlertClassificationRequest, AnalysisRouteRequest, AnalysisRouteResponse
from models.analysis import (
    AnalysisBatchBySidRequest,
    AnalysisBatchBySidResponse,
    AnalysisRunRequest,
    SocAnalysisResult,
)
from models.handoff import SplunkAlertIngest
from models.observability import ObservabilityRunRequest
from services.alert.alert_pipeline import enrich_alert_from_splunk
from services.alert.alert_classifier_llm import classify_alert_hybrid
from services.alert.alert_mcp_enrichment import classify_with_optional_mcp
from services.soc_analysis.analysis_complete_log import log_analysis_complete
from services.observability_analysis import run_observability_analysis
from services.soc_analysis import append_analysis_log, run_analysis
from services.soc_analysis.soc_analysis_batch import run_analysis_batch_by_sid
from services.inventory.inventory_loader import IncompleteOfflineInventoryError, load_inventory_tables
from services.soc_analysis.analysis_audit import (
    build_analysis_input,
    build_analysis_output,
    build_raw_alert,
    resolve_row_index,
)
from services.splunk_json_store import persist_agentic_ops_route_to_splunk

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/classification/alert",
    dependencies=[Depends(check_ingest_bearer), Depends(rate_limit_sensitive)],
)
async def classify_alert_endpoint(
    request: Request,
    body: AlertClassificationRequest,
    settings: Settings = Depends(get_settings),
) -> dict:
    rows = list(body.splunk_results or [])
    if not rows and body.sid:
        try:
            enriched = await enrich_alert_from_splunk(
                SplunkAlertIngest(sid=body.sid, search_name=body.search_name, normalized=body.normalized),
                settings,
            )
            rows = list(enriched.get("splunk_results") or [])
        except AppError:
            raise
        except Exception as e:
            logger.warning("api POST /classification/alert rid=%s enrich failed: %s", http_rid(request), e, exc_info=True)
            raise map_exception(e, context="classification alert enrich") from e

    out = await classify_alert_hybrid(settings, body.normalized, body.search_name, rows, sid=body.sid)
    logger.info(
        "api POST /classification/alert rid=%s sid=%s track=%s pipeline=%s confidence=%.2f",
        http_rid(request),
        body.sid,
        out.track,
        out.recommended_pipeline,
        out.confidence,
    )
    return out.model_dump(mode="json")


@router.post(
    "/analysis/run",
    dependencies=[Depends(check_ingest_bearer), Depends(rate_limit_sensitive)],
    response_model=SocAnalysisResult,
)
async def run_soc_analysis_endpoint(
    request: Request,
    body: AnalysisRunRequest,
    settings: Settings = Depends(get_settings),
) -> SocAnalysisResult:
    """
    Full SOC analysis: Asset Identity (unless ``enrichment`` is supplied) + Defender / Hunter / Judge.

    Uses LiteLLM for structured JSON output when configured; otherwise rule-based fallback.
    Loads inventory from PostgreSQL unless ``users``, ``assets``, and ``relationships`` are all provided inline.
    """
    t0 = time.perf_counter()
    offline = body.users is not None and body.assets is not None and body.relationships is not None
    logger.info(
        "api POST /analysis/run rid=%s sid=%s search_name=%s offline_inventory=%s splunk_result_rows=%d",
        http_rid(request),
        body.sid,
        body.search_name,
        offline,
        len(body.splunk_results or ()),
    )
    try:
        users, assets, relationships = await load_inventory_tables(
            settings, body.users, body.assets, body.relationships
        )
    except IncompleteOfflineInventoryError as e:
        logger.warning("api POST /analysis/run rid=%s inventory 400: %s", http_rid(request), e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        logger.warning("api POST /analysis/run rid=%s inventory 503: %s", http_rid(request), e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.warning(
            "api POST /analysis/run rid=%s inventory 502: %s",
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=502,
            detail="Inventory load failed (check app name, transforms, and permissions): {0}".format(e),
        ) from e

    logger.info(
        "api POST /analysis/run rid=%s tables users=%d assets=%d relationships=%d",
        http_rid(request),
        len(users),
        len(assets),
        len(relationships),
    )
    rows = list(body.splunk_results or [])
    row_index = resolve_row_index(body.row_index, rows)
    result = await run_analysis(
        settings,
        body,
        users=users,
        assets=assets,
        relationships=relationships,
        analysis_row_index=row_index,
    )
    append_analysis_log(settings, result)
    duration_ms = (time.perf_counter() - t0) * 1000.0
    logger.info(
        "api POST /analysis/run rid=%s done sid=%s row_index=%d verdict=%s duration_ms=%.1f",
        http_rid(request),
        body.sid,
        row_index,
        result.judge.verdict,
        duration_ms,
    )
    log_analysis_complete(
        pipeline="api/analysis/run",
        sid=body.sid,
        row_index=row_index,
        verdict=result.judge.verdict,
        priority=result.judge.priority,
        duration_ms=duration_ms,
    )
    return result


@router.post(
    "/analysis/route",
    dependencies=[Depends(check_ingest_bearer), Depends(rate_limit_sensitive)],
    response_model=AnalysisRouteResponse,
)
async def run_routed_analysis_endpoint(
    request: Request,
    body: AnalysisRouteRequest,
    settings: Settings = Depends(get_settings),
) -> AnalysisRouteResponse:
    """
    Classify the alert into Security / Observability and execute corresponding pipeline(s).
    """
    t0 = time.perf_counter()
    offline = body.users is not None and body.assets is not None and body.relationships is not None
    logger.info(
        "api POST /analysis/route rid=%s sid=%s search_name=%s offline_inventory=%s splunk_result_rows=%d",
        http_rid(request),
        body.sid,
        body.search_name,
        offline,
        len(body.splunk_results or ()),
    )
    try:
        users, assets, relationships = await load_inventory_tables(
            settings, body.users, body.assets, body.relationships
        )
    except IncompleteOfflineInventoryError as e:
        logger.warning("api POST /analysis/route rid=%s inventory 400: %s", http_rid(request), e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        logger.warning("api POST /analysis/route rid=%s inventory 503: %s", http_rid(request), e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.warning(
            "api POST /analysis/route rid=%s inventory 502: %s",
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=502,
            detail="Inventory load failed (check app name, transforms, and permissions): {0}".format(e),
        ) from e

    rows = list(body.splunk_results or [])
    if not rows and body.sid:
        try:
            enriched = await enrich_alert_from_splunk(
                SplunkAlertIngest(sid=body.sid, search_name=body.search_name, normalized=body.normalized),
                settings,
            )
            rows = list(enriched.get("splunk_results") or [])
        except AppError:
            raise
        except Exception as e:
            logger.warning("api POST /analysis/route rid=%s enrich failed: %s", http_rid(request), e, exc_info=True)
            raise map_exception(e, context="analysis route enrich") from e

    row_index = resolve_row_index(body.row_index, rows)
    if rows and row_index >= len(rows):
        row_index = len(rows) - 1
    row_slice = [rows[row_index]] if rows else []
    raw_alert = build_raw_alert(
        sid=body.sid,
        search_name=body.search_name,
        normalized=body.normalized,
        splunk_results=rows,
        row_index=row_index,
    )
    analysis_input = build_analysis_input(
        search_name=body.search_name,
        normalized=body.normalized,
        splunk_results=rows,
        row_index=row_index,
    )

    classification, mcp_context, mcp_used = await classify_with_optional_mcp(
        settings,
        normalized=body.normalized,
        search_name=body.search_name,
        splunk_results=row_slice or rows,
        sid=body.sid,
    )
    security_result = None
    observability_result = None
    analysis_output = None

    if classification.recommended_pipeline == "security":
        sec_body = AnalysisRunRequest(
            normalized=body.normalized,
            search_name=body.search_name,
            sid=body.sid,
            row_index=row_index,
            splunk_results=row_slice or rows,
            enrichment=body.enrichment,
        )
        security_result = await run_analysis(
            settings,
            sec_body,
            users=users,
            assets=assets,
            relationships=relationships,
            analysis_row_index=row_index,
        )
        append_analysis_log(settings, security_result)
        analysis_output = build_analysis_output(security_result)

    elif classification.recommended_pipeline == "observability":
        obs_body = ObservabilityRunRequest(
            normalized=body.normalized,
            search_name=body.search_name,
            sid=body.sid,
            row_index=row_index,
            splunk_results=row_slice or rows,
            enrichment=body.enrichment,
        )
        observability_result = await run_observability_analysis(
            settings,
            obs_body,
            users=users,
            assets=assets,
            relationships=relationships,
            analysis_row_index=row_index,
        )

    await persist_agentic_ops_route_to_splunk(
        settings,
        sid=body.sid,
        search_name=body.search_name,
        classification=classification,
        security_result=security_result,
        observability_result=observability_result,
        mcp_context=mcp_context,
        mcp_used=mcp_used,
        row_index=row_index,
        raw_alert=raw_alert,
        analysis_input=analysis_input,
        analysis_output=analysis_output,
    )

    duration_ms = (time.perf_counter() - t0) * 1000.0
    logger.info(
        "api POST /analysis/route rid=%s done sid=%s row_index=%d track=%s pipeline=%s duration_ms=%.1f",
        http_rid(request),
        body.sid,
        row_index,
        classification.track,
        classification.recommended_pipeline,
        duration_ms,
    )
    verdict = None
    priority = None
    if security_result is not None:
        verdict = security_result.judge.verdict
        priority = security_result.judge.priority
    elif observability_result is not None:
        verdict = observability_result.ops_judge.verdict
        priority = observability_result.ops_judge.priority
    log_analysis_complete(
        pipeline="api/analysis/route",
        sid=body.sid,
        row_index=row_index,
        verdict=verdict,
        priority=priority,
        duration_ms=duration_ms,
        extra="track={0} recommended_pipeline={1}".format(
            classification.track,
            classification.recommended_pipeline,
        ),
    )
    return AnalysisRouteResponse(
        track=classification.track,
        classification=classification,
        security_result=security_result,
        observability_result=observability_result,
        mcp_used=mcp_used,
        mcp_context=mcp_context,
        row_index=row_index,
        raw_alert=raw_alert,
        analysis_input=analysis_input,
        analysis_output=analysis_output,
    )


@router.post(
    "/analysis/run-by-sid",
    dependencies=[Depends(check_ingest_bearer), Depends(rate_limit_sensitive)],
    response_model=AnalysisBatchBySidResponse,
)
async def run_soc_analysis_batch_by_sid_endpoint(
    request: Request,
    body: AnalysisBatchBySidRequest,
    settings: Settings = Depends(get_settings),
) -> AnalysisBatchBySidResponse:
    """
    Splunk REST: fetch all rows for ``sid``, then run Defender / Hunter / Judge **per row**
    (merged ``normalized`` + single-row ``splunk_results`` for each).

    Respects ``max_rows`` to limit cost. Use ``stop_on_first_error`` to fail fast on exceptions.
    """
    t0 = time.perf_counter()
    offline = body.users is not None and body.assets is not None and body.relationships is not None
    logger.info(
        "api POST /analysis/run-by-sid rid=%s sid=%s search_name=%s max_rows=%s stop_on_first_error=%s offline_inventory=%s",
        http_rid(request),
        body.sid,
        body.search_name,
        body.max_rows,
        body.stop_on_first_error,
        offline,
    )
    try:
        users, assets, relationships = await load_inventory_tables(
            settings, body.users, body.assets, body.relationships
        )
    except IncompleteOfflineInventoryError as e:
        logger.warning("api POST /analysis/run-by-sid rid=%s inventory 400: %s", http_rid(request), e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        logger.warning("api POST /analysis/run-by-sid rid=%s inventory 503: %s", http_rid(request), e)
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.warning(
            "api POST /analysis/run-by-sid rid=%s inventory 502: %s",
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=502,
            detail="Inventory load failed (check app name, transforms, and permissions): {0}".format(e),
        ) from e

    try:
        out = await run_analysis_batch_by_sid(settings, body, users=users, assets=assets, relationships=relationships)
    except ValueError as e:
        logger.warning("api POST /analysis/run-by-sid rid=%s batch 400: %s", http_rid(request), e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.warning(
            "api POST /analysis/run-by-sid rid=%s batch 502: %s",
            http_rid(request),
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail="Splunk REST or batch analysis failed: {0}".format(e)) from e
    ok_n = sum(1 for r in out.rows if r.ok)
    fail_n = sum(1 for r in out.rows if not r.ok)
    duration_ms = (time.perf_counter() - t0) * 1000.0
    logger.info(
        "api POST /analysis/run-by-sid rid=%s done sid=%s analyzed=%d ok=%d fail=%d duration_ms=%.1f",
        http_rid(request),
        body.sid,
        out.analyzed_row_count,
        ok_n,
        fail_n,
        duration_ms,
    )
    log_analysis_complete(
        pipeline="api/analysis/run-by-sid",
        sid=body.sid,
        duration_ms=duration_ms,
        extra="analyzed={0} ok={1} fail={2}".format(out.analyzed_row_count, ok_n, fail_n),
    )
    return out
